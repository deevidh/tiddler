from typing import Container
from dateutil import parser
import arrow
from ics import Calendar, Event
datafile="/Users/davidh/tmp/tide_data.txt"
icsfile="/Users/davidh/tmp/tiddler.ics"

c = Calendar()
c.creator = "Tiddler"

def get_input():
    with open(datafile) as f:
        data_lines = f.read().splitlines()
    strings = [ line.split(",") for line in data_lines ]
    return [[arrow.get(f"{date} {time}", 'YYYY-MM-DD h:mm a ZZZ'),height,event] for [location,date,time,height,event] in strings]

def get_windows(tide_data):
    rising_time=""
    high_time=""
    high_level=""
    for event in tide_data:
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
            c.events.add(e)
    return c

def write_file(tide_calendar):
    with open(icsfile, 'w') as my_file:
        my_file.writelines(tide_calendar)

tide_data=get_input()
tide_calendar=get_windows(tide_data)
write_file(tide_calendar)