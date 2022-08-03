# Tiddler

---

## Overview

This CDK projects creates an application which periodically generates tidal predictions for a given location, extracts some specific information from the predictions and uses it to create an iCalendar file in an S3 bucket which can be subscribed to from an external calendar app.

The structure of the project is based on this example: https://github.com/aws-samples/aws-cdk-examples/tree/master/python/s3-object-lambda

## Components

- Private S3 bucket for holding intermediate files
- Public S3 bucket which points to the public S3 bucket
- Scheduled event in EventBridge which is used to trigger the state machine in Step Functions
- Step Functions state machine which only has two steps:
  - Run a task on an ECS cluster. The task runs a pre-built docker image which uses XTide to generate tide predictions for Leith. This is output to a CSV file in the private S3 bucket.
  - Run a Lambda function which reads the CSV file, transforms the data and writes it out to an iCal file in the public S3 bucket.

--

## Build and Deploy

The `cdk.json` file tells the CDK Toolkit how to execute your app.

### Python setup

This project is set up like a standard Python project. The initialization process also creates a virtualenv within this
project, stored under the `.env` directory. To create the virtualenv it assumes that there is a `python3` (or `python`
for Windows) executable in your path with access to the `venv` package. If for any reason the automatic creation of the
virtualenv fails, you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

### CDK Deploy

With specific profile,
```
$ cdk deploy --profile test
```

Using the default profile

```
$ cdk deploy
```

---

## Future improvements

- Allow data to be generated for multiple locations, or a custom threshold of depth
- Adding an ASCII chart in the calendar event description
- In the event description, provide a link to a URL to get more detailed information for that specific day
- Add the Feed name into the iCal file
