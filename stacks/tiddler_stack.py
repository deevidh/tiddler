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
    aws_ecr_assets as ecr_assets,
    aws_logs as logs,
    aws_events as events,
    aws_events_targets as events_targets
)

# TODO: Split this stack up into more logical chunks
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

        # TODO: don't hardcode this, or move it up a level?
        zone_name = "sandbox.deevid.net"
        record_name = "tiddler"

        # Get the default VPC (for the ECS cluster)
        vpc = ec2.Vpc.from_lookup(self, "Vpc",
            is_default=True
        )

        # Create an ECS cluster for running xtide containers
        cluster = ecs.Cluster(self, "TiddlerCluster", vpc=vpc
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
            execution_role=tiddler_task_execution_role,
        )

        # Create the container definition
        container_definition = task_definition.add_container("XTideContainer",
            image=ecs.ContainerImage.from_registry(xtide_container_image.image_uri),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="/tiddler",
                log_retention=logs.RetentionDays.ONE_WEEK
            )
        )

        #status_lambda = _lambda.Function(self, 'statusLambda',
        #                                 handler='lambda_function.lambda_handler',
        #                                 runtime=_lambda.Runtime.PYTHON_3_9,
        #                                 code=_lambda.Code.from_asset('lambda/status'))



        #status_check_task = sfn_tasks.LambdaInvoke(
        #    self, "StatusCheckLambda",
        #    lambda_function=status_lambda,
        #    output_path="$.status_lambda",
        #)

        #wait_job = sfn.Wait(
        #    self, "Wait 30 Seconds",
        #    time=sfn.WaitTime.duration(
        #        Duration.seconds(60))
        #)

        #fail_job = sfn.Fail(
        #    self, "Fail",
        #    cause='Tiddler failed',
        #    error='Tiddler failed'
        #)

        #succeed_job = sfn.Succeed(
        #    self, "Succeeded",
        #    comment='Tiddler succeeded'
        #)


        # Set up a public bucket to serve the iCal file
        bucket_public = s3.Bucket(self, "tiddler",
            bucket_name=f"{record_name}.{zone_name}", # This must match the R53 domain name
            access_control=s3.BucketAccessControl.PUBLIC_READ,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        public_zone = route53.HostedZone.from_lookup(self, "public_zone",
            domain_name=zone_name
        )

        # Use CNAME for an S3 bucket, ALIAS for an S3 website
        #r53_bucket_record = route53.ARecord(self, "S3BucketRecord",
        r53_bucket_record = route53.CnameRecord(self, "S3BucketRecord",
            record_name=record_name,
            zone=public_zone,
            domain_name=bucket_public.bucket_domain_name
        )

        # Set up a private bucket
        bucket_private = s3.Bucket(self, "tiddler-private",
            bucket_name="tiddler-private",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Allow the container to write to the private bucket
        task_definition.add_to_task_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:*Object"],
            resources=[f"{bucket_private.bucket_arn}/*"])
        )

        # Create container overrides to pass in parameters from SFN state to container
        container_overrides=[
            sfn_tasks.ContainerOverride(
                container_definition=container_definition,
                environment=[
                    sfn_tasks.TaskEnvironmentVariable(
                        name="sfn_task_token",
                        value=sfn.JsonPath.string_at("$$.Task.Token")
                    ),
                    sfn_tasks.TaskEnvironmentVariable(
                        name="s3_bucket",
                        value=bucket_private.bucket_name
                    )

                ],
            )
        ]

        # Step functions definitions

        # Create SFN task to run xtide container on ECS
        generate_tidal_data_task = sfn_tasks.EcsRunTask(self, "GenerateTidalDataTask",
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            cluster=cluster,
            task_definition=task_definition,
            assign_public_ip=True,
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC # Doesn't need to be public, but this is all that exists in the default VPC
            ),
            container_overrides=container_overrides,
            launch_target=sfn_tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.LATEST),
            timeout=Duration.seconds(30)
        )

        # IAM: Allow the container to return the token to SFN
        task_definition.add_to_task_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["states:SendTask*"],
            resources=[f"*"])
        )

        # Lambda which creates ics file from tidal data
        # This class in in alpha - it takes care of packaging up your lambda, including any requirements
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
            payload=sfn.TaskInput.from_object({
                "public_bucket": bucket_public.bucket_name,
                "csv_file": sfn.JsonPath.string_at("$.csv_file")
            }),
            output_path="$"
        )

        # IAM: Allow lambda to read and write from S3
        create_ical_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[
                f"{bucket_public.bucket_arn}/*",
                f"{bucket_private.bucket_arn}/*"
            ],
            actions=["s3:*Object","s3:*ObjectAcl"]
        ))

        # IAM: Restrict Lambda to be invoked from own account
        create_ical_lambda.add_permission("invocationRestriction",
                                                          action="lambda:InvokeFunction",
                                                          principal=iam.AccountRootPrincipal(),
                                                          source_account=Aws.ACCOUNT_ID)

        # Create chain for state machine
        definition = generate_tidal_data_task\
            .next(create_ical_lambda_task)\

        # Create state machine
        sm = sfn.StateMachine(
            self, "TiddlerStateMachine",
            definition=definition,
            timeout=Duration.minutes(5),
        )

        #Schedule the state machine to run every week
        scheduled_event_rule = events.Rule(self, "WeeklySchedule",
            description="Trigger the Tiddler state machine on a schedule",
            schedule=events.Schedule.cron(minute="0",hour="9",month="*",week_day="4",year="*"),
            targets=[
               events_targets.SfnStateMachine(sm)
            ]
        )
