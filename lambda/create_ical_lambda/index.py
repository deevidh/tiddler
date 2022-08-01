# Lambda script to transorm tidal data and output an iCalendar file
# Data is retrieved from a CSV file at the specified location in S3
# Data is transformed and written to an .ics (iCalendar) file in the sepcified S3 bucket
#
# The Lambda'sinput event should contain the following information:
# {
#   "source_bucket": "tiddler-app-private",
#   "source_file": "tidal_data/tidal_data.txt",
#   "dest_bucket": "tiddler-app",
#   "dest_file": "tide_calendar.ics"
# }

# TODO: Better checking for errors during parsing/transformation

import boto3
import json
import arrow
from ics import Calendar, Event

def handler(event, context):
    status=True
    print(f"Create_ical_lambda was invoked")
    print(f"event: {event}")
    if not {"csv_file", "public_bucket"} <= event.keys():
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error: invalid event parameters"
                }
            )
        }

    tidal_data = getTidalDataFile(event['csv_file'])
    parsed_tidal_data = parseTidalData(tidal_data)
    ical_data = createIcalData(parsed_tidal_data)
    status = putIcalFile(event['public_bucket'], ical_data)

    return {
        "statusCode": 200 if status == True else 500,
        "body": json.dumps({
            "message": "Success" if status == True else "Failed"
        })
    }

def split_s3_path(s3_path):
    path_parts=s3_path.replace("s3://","").split("/")
    bucket=path_parts.pop(0)
    key="/".join(path_parts)
    return bucket, key

# Retrieve tidal data from specified location in S3
def getTidalDataFile(csv_file: str) -> str:
    print(f"Getting tidal data file from: {csv_file}")
    source_bucket, source_file = split_s3_path(csv_file)
    s3_client = boto3.client("s3")
    file_content = s3_client.get_object(
        Bucket=source_bucket,
        Key=source_file
    )["Body"].read()
    return file_content.decode()

# Parse the tidal data file
def parseTidalData(tidal_data: str) -> list:
    print("Parsing tidal data")
    tide_events = [ event for event in tidal_data.split('\n') if event ] # Split to list and remove empty strings
    event_fields = [ line.split(",") for line in tide_events ]
    parsed_events = [[arrow.get(f"{date} {time}", 'YYYY-MM-DD h:mm a ZZZ'),height,event] for [location,date,time,height,event] in event_fields]
    return parsed_events

# Transform tidal data and use ics module to write a calendar in iCalendar format
def createIcalData(parsed_tidal_data: list) -> str:
    print("Transforming tidal data to iCal format")
    tide_cal = Calendar()
    tide_cal.creator = "Tiddler"

    rising_time=""
    high_time=""
    high_level=""
    for event in parsed_tidal_data:
        if event[2] == "Mark Rising":
            rising_time=event[0]
        if event[2] == "High Tide":
            high_time=event[0]
            high_level=event[1]
        if event[2] == "Mark Falling" and rising_time:
            falling_time=event[0]
            e = Event()
            e.name = f"High tide at {high_time.to('Europe/London').format('HH:mm')} ({high_level})"
            e.begin = rising_time
            e.end = falling_time
            e.location = "Leith, UK"
            e.description = f"""Tide at Leith >3.0m from {rising_time.to('Europe/London').format('HH:mm')} to {falling_time.to('Europe/London').format('HH:mm')}.
High tide is at {high_time.to('Europe/London').format('HH:mm')} ({high_level})

This event was created automatically by Tiddler, see http://deevid.com/tiddler for more info"""
            tide_cal.events.add(e)
    return tide_cal

# Put the ics file into the specified S3 bucket
def putIcalFile(public_bucket: str, ical_data: str) -> bool:
    dest_file="tides-leith.ics"
    print(f"Writing iCal file to: s3://{public_bucket}/{dest_file}")
    s3_client = boto3.client("s3")
    response = s3_client.put_object(
        ACL='public-read', # Object is public, iCal feeds will get this object directly from S3
        Bucket=public_bucket,
        Key=dest_file,
        Body=ical_data.serialize()
    )
    if response.get('ResponseMetadata').get('HTTPStatusCode') == 200:
        print('File Uploaded to S3 successfully')
        return True
    else:
        print('Error: File not uploaded to S3')
        return False
