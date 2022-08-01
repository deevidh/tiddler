# XTide Dockerfile

## Overview

The docker image is based on Ubuntu. It uses xtide to generate tidal data for Leith, and uploads as a csv file to an S3 bucket.
The S3 bucket name should be provided in the `s3_bucket` env var. The Step Functions task token should be set in the `task_token` env var.

## Development

### Build Locally

```bash
docker build -t xtide-ubuntu .
```

## Run Locally

Override entrypoint to grab an interactive shell on the container for development/debugging

```bash
docker run -it --entrypoint /bin/bash xtide-ubuntu
```

Information on xtide CLI usage can be found here:

- [XTide - Using the command line interface](https://flaterco.com/xtide/tty.html)
- [XTide - Modes](https://flaterco.com/xtide/modes.html)
