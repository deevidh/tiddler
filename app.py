from aws_cdk import App
from stacks.tiddler_s3_lambda_stack import TiddlerS3LambdaStack

app = App()
TiddlerS3LambdaStack(app, "TiddlerApp")
app.synth()
