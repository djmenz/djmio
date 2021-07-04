import datetime
import json
from datetime import date

def epoch_to_local_time(epoch_time):
    date = datetime.datetime.fromtimestamp(epoch_time).strftime('%d-%m-%Y')
    return date

def epoch_to_ordinal(epoch_time):
    ordinal = date.toordinal(datetime.datetime.fromtimestamp(epoch_time))
    return ordinal

def ordinal_to_str(ordinal):
    date_str = date.fromordinal(ordinal).strftime('%d-%m-%Y')
    return date_str

def ordinal_to_str_iso(ordinal):
    date_str = date.fromordinal(ordinal).strftime('%Y%m%d')
    return date_str

def local_date_str_to_epoch(strdate, date_string):
    datetime_object = datetime.datetime.strptime(strdate, date_string)
    timestamp = datetime.datetime.timestamp(datetime_object)
    return timestamp

def local_date_str_to_ordinal(strdate, date_string):
    datetime_object = datetime.datetime.strptime(strdate, date_string).date()
    ordinal = date.toordinal(datetime_object)
    return ordinal

def convert_ord_to_day_of_week(ordinal):
    day_of_week_int = date.fromordinal(ordinal).weekday()
    return day_of_week_int

def convert_mins_to_hrmins_str(minutes):
    mins =  ("{:.0f}".format(minutes%60)).zfill(2)
    return (str(int(minutes/60)) + ":" + mins)