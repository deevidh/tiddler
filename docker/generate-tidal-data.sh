#!/bin/bash

# This script generates tidal data using xtide and uploads the resulting CSV file to an S3 bucket
#
# This script expects the following env vars to be set:
# s3_bucket - The name of the S3 bucket to upload the CSV file to
# sfn_task_token - The task token so that we can call back to SFN
#

S3_BUCKET=$s3_bucket
TASK_TOKEN=$sfn_task_token
LOCAL_FILE=tidal_data_leith_$(date +%d%m%y-%H%M%S).csv
S3_FILE="s3://${S3_BUCKET}/${LOCAL_FILE}"

echo "Running $0 at ${date}"
echo S3_BUCKET=$s3_bucket
echo TASK_TOKEN=$sfn_task_token
echo LOCAL_FILE=tidal_data_leith_$(date +%d%m%y-%H%M%S).csv
echo S3_FILE="s3://${S3_BUCKET}/${LOCAL_FILE}"

cd ~
touch .disableXTidedisclaimer

# -l leith    location
# -pi 90      predict interval (Number of days of predictions to generate when no end time is specified)
# -ml 3.0m    mark level
# -fc         format csv
# -zy         zulu time yes (Coerce all time zones to UTC)
XTIDE_PARAMS="-l leith -pi 90 -ml 3.0m -fc -zy"

echo "Generating tidal data with: /usr/bin/tide ${XTIDE_PARAMS}"
if /usr/bin/tide ${XTIDE_PARAMS} > $LOCAL_FILE && aws s3 cp $LOCAL_FILE $S3_FILE; then
    echo "Tidal data file uploaded to $S3_FILE"
    echo "Sending task success to Step Functions using token"
    TASK_OUTPUT='{"csv_file": "'${S3_FILE}'"}'
    aws stepfunctions send-task-success --task-token "$TASK_TOKEN" --task-output "$TASK_OUTPUT"
else
    echo "Failed to generate and upload Tidal data file to $S3_FILE"
    echo "Sending Task failure to Step Functions using token"
    aws stepfunctions send-task-failure --task-token "$TASK_TOKEN" --error "Application Execution Failed" --cause "There was an error generating tidal data using xtide, or uploading data to S3"
fi
