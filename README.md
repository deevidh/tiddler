Tiddler
---

## Overview

This CDK projects aims to create an application which can read tidal data from a file, and export the data to an ical file in an S3 bucket.
The structure of the project is based on this example: https://github.com/aws-samples/aws-cdk-examples/tree/master/python/s3-object-lambda

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

## Project TODO

- Add a custom domain
- Create a state machine to generate the tidal data and trigger the lambda

## Project Log

- Got the CDK project building and deploying
- Started to modify the code to make objects public and remove S3 access points
- Tested that example ICS file works and can be served from the S3 bucket.
- Created a basic Python file (currently just runs locally) to create the ICS data
- Updated the CDK stacks to correctly deploy S3, Lambda and supporting resources
- Started adding a CNAME to the S3 bucket in a custom R53 zone, but this isn't complete
- Updated the Lambda function to correctly transform the data file

## Future improvements

- Allow data to be generated for multiple locations, or a custom threshold of depth
- Adding an ASCII chart in the calendar event description
- In the event description, provide a link to a URL to get more detailed information for that specific day
- Add the Feed name into the iCal file
