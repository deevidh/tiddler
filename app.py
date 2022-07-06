from aws_cdk import App
from aws_cdk import Environment
from stacks.tiddler_stack import TiddlerStack

env_sandbox = Environment(account="593130735504", region="eu-west-2")

app = App()
TiddlerStack(app, "TiddlerApp", env_sandbox)
app.synth()
