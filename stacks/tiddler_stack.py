from operator import truediv
from aws_cdk import (
    App,
    Aws,
    CfnOutput,
    Duration,
    Environment,
    Stack,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as lambda_python,
    aws_s3 as s3,
    aws_s3_deployment as s3deployment,
    aws_route53 as route53,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets
)

class TiddlerStack(Stack):
    def __init__(self, app: App, id: str, env: Environment) -> None:
        super().__init__(app, id, env=env)

#        vpc = ec2.Vpc(self, "TiddlerVpc", cidr="10.0.0.0/16", max_azs=2, nat_gateways=0,
#            subnet_configuration=[
#                {
#                    'name':'private-subnet',
#                    'subnetType': ec2.SubnetType.PRIVATE_ISOLATED,
#                    'cidrMask': 24,
#                },
#                {
#                    'name': 'public-subnet',
#                    'subnetType': ec2.SubnetType.PUBLIC,
#                    'cidrMask': 24,
#                }
#            ]
#        )

        # Get the default VPC (for the ECS cluster)
        vpc = ec2.Vpc.from_lookup(self, "Vpc",
            is_default=True
        )

        # Create an ECS cluster
        cluster = ecs.Cluster(self, "TiddlerCluster", vpc=vpc
            #enable_fargate_capacity_providers=True,
        )

        # Bundle XTide Docker container and upload to ECR
        xtide_container_image = ecr_assets.DockerImageAsset(self, "XTideContainerImage", directory="docker")

        # Create a task execution role using the AWS managed policy so we can retrieve the image from ECR
        tiddler_task_execution_role = iam.Role(self, 'ECSExecutionRole',
            role_name="TiddlerECSTaskExecutionRole",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonECSTaskExecutionRolePolicy')
            ],
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )

        # Create the ECS task def
        task_definition = ecs.TaskDefinition(self, "TiddlerTaskDef",
            compatibility=ecs.Compatibility.FARGATE,
            cpu="512",
            memory_mib="1024",
            execution_role=tiddler_task_execution_role
        )
        task_definition.add_container("XTideContainer",
            image=ecs.ContainerImage.from_registry(xtide_container_image.image_uri)
        )

        # Lambda Handlers Definitions
        #submit_lambda = _lambda.Function(self, 'submitLambda',
        #                                 handler='lambda_function.lambda_handler',
        #                                 runtime=_lambda.Runtime.PYTHON_3_9,
        #                                 code=_lambda.Code.from_asset('lambda/submit'))

        status_lambda = _lambda.Function(self, 'statusLambda',
                                         handler='lambda_function.lambda_handler',
                                         runtime=_lambda.Runtime.PYTHON_3_9,
                                         code=_lambda.Code.from_asset('lambda/status'))

        # Step functions Definition
        # TODO: Add timeout
        generate_tidal_data_task = sfn_tasks.EcsRunTask(self, "GenerateTidalDataTask",
            #integration_pattern=sfn.IntegrationPattern.RUN_JOB, # TODO Improve integration, use token?
            integration_pattern=sfn.IntegrationPattern.REQUEST_RESPONSE, # TODO Improve integration, use token?
            cluster=cluster,
            task_definition=task_definition,
            assign_public_ip=True,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC # Doesn't need to be public, but this is all that exists in the default VPC
            ),
            launch_target=sfn_tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.LATEST)
        )

        # lambda to create ics file from tidal data
        create_ical_lambda = lambda_python.PythonFunction(
            self, "create_ical_lambda",
            entry="lambda/create_ical_lambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=Duration.seconds(15),
            handler="handler"
        )

        create_ical_lambda_task = sfn_tasks.LambdaInvoke(
            self, "CreateIcalLambda",
            lambda_function=create_ical_lambda,
            output_path="$.ical_lambda",
        )

        status_check_task = sfn_tasks.LambdaInvoke(
            self, "StatusCheckLambda",
            lambda_function=status_lambda,
            output_path="$.status_lambda",
        )

        wait_job = sfn.Wait(
            self, "Wait 30 Seconds",
            time=sfn.WaitTime.duration(
                Duration.seconds(60))
        )

        fail_job = sfn.Fail(
            self, "Fail",
            cause='Tiddler failed',
            error='Tiddler failed'
        )

        succeed_job = sfn.Succeed(
            self, "Succeeded",
            comment='Tiddler succeeded'
        )

        # Create chain for state machine
        definition = generate_tidal_data_task\
            .next(wait_job)\
            .next(create_ical_lambda_task)\
            .next(status_check_task)\
            .next(sfn.Choice(self, 'Job Complete?')
                  .when(sfn.Condition.string_equals('$.status', 'FAILED'), fail_job)
                  .when(sfn.Condition.string_equals('$.status', 'SUCCEEDED'), succeed_job)
                  .otherwise(wait_job))

        # Create state machine
        sm = sfn.StateMachine(
            self, "TiddlerStateMachine",
            definition=definition,
            timeout=Duration.minutes(5),
        )

        # Set up a public bucket to serve the iCal file
        bucket = s3.Bucket(self, "tiddler",
            bucket_name="tiddler-app",
            access_control=s3.BucketAccessControl.PUBLIC_READ,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        public_zone = route53.HostedZone.from_lookup(self, "public_zone",
            domain_name="sandbox.deevid.net" # FIXME don't hardcode this
        )

        r53_bucket_record = route53.CnameRecord(self, "S3BucketRecord",
        # CNAME for an S3 bucket, ALIAS for an S3 website
            record_name="tiddler",
            zone=public_zone,
            domain_name=bucket.bucket_domain_name
        )

        # Set up a private bucket
        bucket_private = s3.Bucket(self, "tiddler-private",
            bucket_name="tiddler-app-private",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            #access_control=s3.BucketAccessControl.PRIVATE,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # FIXME: Remove this when the tidal data is generated programatically
        # Populate bucket with tidal data
        s3deployment.BucketDeployment(self, "TidalDataFiles",
            sources=[s3deployment.Source.asset("./s3-data")],
            destination_bucket=bucket_private,
            destination_key_prefix="tidal_data"
        )


        # lambda s3 access
        create_ical_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"{bucket.bucket_arn}/*",
                f"{bucket_private.bucket_arn}/*"
            ],
            actions=["s3:*Object","s3:*ObjectAcl"]
        ))

        # Restrict Lambda to be invoked from own account
        create_ical_lambda.add_permission("invocationRestriction",
                                                          action="lambda:InvokeFunction",
                                                          principal=iam.AccountRootPrincipal(),
                                                          source_account=Aws.ACCOUNT_ID)

        CfnOutput(self, "publicBucketArn", value=bucket.bucket_arn)
        CfnOutput(self, "privateBucketArn", value=bucket_private.bucket_arn)
        CfnOutput(self, "createIcalLambdaArn",
                      value=create_ical_lambda.function_arn)
