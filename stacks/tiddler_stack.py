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
    aws_s3objectlambda as s3_object_lambda,
)

class TiddlerStack(Stack):
    def __init__(self, app: App, id: str, env: Environment) -> None:
        super().__init__(app, id, env=env)

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

        # lambda to create ics file from tidal data
        create_ical_lambda = lambda_python.PythonFunction(
            self, "create_ical_lambda",
            entry="lambda/create_ical_lambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            timeout=Duration.seconds(15),
            handler="handler"
            #code=_lambda.Code.from_asset("lambda/create_ical_lambda"))
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
