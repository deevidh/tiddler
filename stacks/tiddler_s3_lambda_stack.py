from aws_cdk import (
    App,
    Aws,
    CfnOutput,
    Stack,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3objectlambda as s3_object_lambda,
)

# configurable variables
S3_ACCESS_POINT_NAME = "example-test-ap"
OBJECT_LAMBDA_ACCESS_POINT_NAME = "s3-object-lambda-ap"


class TiddlerS3LambdaStack(Stack):
    def __init__(self, app: App, id: str) -> None:
        super().__init__(app, id)
        self.access_point = f"arn:aws:s3:{Aws.REGION}:{Aws.ACCOUNT_ID}:accesspoint/" \
                            f"{S3_ACCESS_POINT_NAME}"

        # Set up a public bucket
        bucket = s3.Bucket(self, "tiddler",
                           access_control=s3.BucketAccessControl.PUBLIC_READ,
                           encryption=s3.BucketEncryption.S3_MANAGED
                           )

        # lambda to process our objects during retrieval
        retrieve_transformed_object_lambda = _lambda.Function(
            self, "retrieve_transformed_obj_lambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/retrieve_transformed_object_lambda"))

        # Object lambda s3 access
        retrieve_transformed_object_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["s3-object-lambda:WriteGetObjectResponse"]
        ))
        # Restrict Lambda to be invoked from own account
        retrieve_transformed_object_lambda.add_permission("invocationRestriction",
                                                          action="lambda:InvokeFunction",
                                                          principal=iam.AccountRootPrincipal(),
                                                          source_account=Aws.ACCOUNT_ID)

        CfnOutput(self, "exampleBucketArn", value=bucket.bucket_arn)
        CfnOutput(self, "objectLambdaArn",
                      value=retrieve_transformed_object_lambda.function_arn)
