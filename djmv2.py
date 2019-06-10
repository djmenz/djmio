import requests
import arrow
import boto3
import math
import datetime
from datetime import date
import collections
from io import StringIO

from flask import Flask
from flask import request
from flask import render_template
from requests.auth import HTTPBasicAuth

week_day = ['M','T','W','T','F','S','S']

app = Flask(__name__)

@app.route("/")
def main_page():

    buf = StringIO()
    buf.write("DJM.IO<br><br>")
    
    # Get all the user data from each service
    refresh_withings_token()
    refresh_fitbit_token()

    auth_urls = get_user_data()

    data_strava = get_data_from_site(auth_urls['strava']['url'] + auth_urls['strava']['access_token'])
    data_tye = get_data_from_site(auth_urls['tye']['url'])[::-1]
    data_withings = get_data_withings(auth_urls['withings']['url'], {"Authorization": "Bearer {}".format(auth_urls['withings']['auth_token_dm'])})
    data_fitbit_step = get_step_data_fitbit(auth_urls['fitbit']['url_steps'], {"Authorization": "Bearer {}".format(auth_urls['fitbit']['access_token'])})[::-1]
    
    #First day of 2018 instead 
    earliest_date = local_date_str_to_ordinal('01-01-2018', '%d-%m-%Y')
    todays_date_epoch = int(datetime.datetime.now().timestamp())
    todays_date = date.toordinal(datetime.datetime.fromtimestamp(todays_date_epoch))

    start_time = arrow.utcnow()
    allDays = collections.OrderedDict()
    for day in range(earliest_date,todays_date+1):
        
        tempday = OneDay()
        tempday.date = day
        allDays[day]= tempday

    # populate strava data
    for date_entry in data_strava:
        this_day =  epoch_to_ordinal(local_date_str_to_epoch(date_entry['start_date_local'],'%Y-%m-%dT%H:%M:%SZ'))
        temp_strava_activity = StravaActivity(
            strava_date = date_entry['start_date_local'], 
            strava_description = date_entry['name'], 
            strava_distance=date_entry['distance'],
            strava_time=date_entry['elapsed_time'],
            strava_type=date_entry['type']
        )

        try:
            #print(temp_strava_activity)
            allDays[this_day].strava_activities.append(temp_strava_activity)
        except KeyError:
            #print('Key Error Error Strava')
            continue

    # populate tye data
    for data_entry in data_tye:
        this_day = local_date_str_to_ordinal(data_entry['date'], '%Y-%m-%d')
        try:
            allDays[this_day].carbs = data_entry['carbs']
            allDays[this_day].calories = data_entry['calories']
            allDays[this_day].protein = data_entry['protein']
            allDays[this_day].fat = data_entry['fats']
        except KeyError:
            #print('key error tye')
            continue

    #populate withings data
    for data_entry in data_withings:
        this_day = epoch_to_ordinal(data_entry['date'])
        try:
            t_weight = data_entry['measures'][0]['value']
            t_unit = data_entry['measures'][0]['unit']
            t_date = data_entry['date']
            t_date_human = epoch_to_local_time(t_date)
            tempweight = ("%.2f" % (t_weight/math.pow(10,-t_unit)))
            allDays[this_day].bodyweight = tempweight
        except KeyError:
            #print('key error withings')
            continue   

    #populate fitbit-step data
    for data_entry in data_fitbit_step:
        this_day = local_date_str_to_ordinal(data_entry['dateTime'], '%Y-%m-%d')
        try:
            temp_steps = data_entry['value']
            allDays[this_day].steps = temp_steps
        except KeyError:
            print('key error fitbit steps')
            continue  

    # Reversing it to make the newest days the lowest array index
    all_days_list = list(allDays)[::-1]

    week_bws = []
    week_steps = []

    for day in all_days_list:
        
        int_day = convert_ord_to_day_of_week(allDays[day].date)

        if (float(allDays[day].bodyweight) > float(0.0)):
            week_bws.append(float(allDays[day].bodyweight))

        if (int(allDays[day].steps) > 50): #50 steps if i used the fitbit 
            week_steps.append(float(allDays[day].steps))


        buf.write(str(allDays[day]) + '<br>')
        if (int_day == 0):
            week_avg_bw = 0.0
            week_avg_steps = 0

            if ((len(week_bws)) > 0):
                week_avg_bw = sum(week_bws) / len(week_bws)

            if ((len(week_steps)) > 0):
                week_avg_steps = sum(week_steps) / len(week_steps)

            buf.write("Week average BW: " + ("{:.2f}".format(week_avg_bw)) + 'kg<br>')
            buf.write("Week average steps: " + ("{:.0f}".format(week_avg_steps)) + '<br>')
            buf.write('<br>')
            week_bws = []
            week_steps = []


    finish_time = arrow.utcnow()
    print(str(finish_time - start_time) + " " + "Generating data array")

    return buf.getvalue()

#import pdb; pdb.set_trace() 

def get_user_data():
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
    table = dynamodb.Table('djmio_platform_urls')
    peak_response = table.scan()

    platform_auth = {}
    for row in peak_response['Items']:
        platform_auth[row['platform']] = row

    return(platform_auth)

def refresh_withings_token():
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
    table = dynamodb.Table('djmio_platform_urls')
    auth_urls = get_user_data()
    url = auth_urls['withings']['url_refresh_token']
    url_api = auth_urls['withings']['url']
    client_id = auth_urls['withings']['client_id']
    client_secret = auth_urls['withings']['client_secret']
    refresh_token = auth_urls['withings']['refresh_token_dm']
    data = {'client_id': client_id, 'grant_type': 'refresh_token', 'client_secret': client_secret, 'refresh_token': refresh_token }
    resp_json = requests.post(url=url, data=data).json()
    print("withings token refreshed")

    table.put_item(
                    Item={
                        'platform': 'withings',
                        'refresh_token_dm': resp_json['refresh_token'],
                        'auth_token_dm': resp_json['access_token'],
                        'url_refresh_token': url,
                        'url': url_api,
                        'client_id': client_id,
                        'client_secret': client_secret,
                    },
                )
    return

def refresh_fitbit_token():
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
    table = dynamodb.Table('djmio_platform_urls')
    auth_urls = get_user_data()
    
    url_refresh_token = auth_urls['fitbit']['url_refresh_token']
    url_steps = auth_urls['fitbit']['url_steps']
    client_id = auth_urls['fitbit']['client_id']
    client_secret = auth_urls['fitbit']['client_secret']
    refresh_token = auth_urls['fitbit']['refresh_token']
    access_token = auth_urls['fitbit']['access_token']

    headers = HTTPBasicAuth(client_id, client_secret)
    data = {'grant_type': 'refresh_token', 'refresh_token': refresh_token }
    
    resp_json = requests.post(url=url_refresh_token, auth=HTTPBasicAuth(client_id, client_secret), data=data).json()
    print("fitbit token refreshed")

    table.put_item(
                    Item={
                        'platform': 'fitbit',
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'url_refresh_token': url_refresh_token,
                        'refresh_token': resp_json['refresh_token'],
                        'access_token': resp_json['access_token'],
                        'url_steps': url_steps,
                    },
                )
    return

def convert_ord_to_day_of_week(ordinal):
    day_of_week_int = date.fromordinal(ordinal).weekday()
    return day_of_week_int

def get_data_from_site(url):
    start_time = arrow.utcnow()
    resp_json = requests.get(url).json()
    finish_time = arrow.utcnow()
    print(str(finish_time - start_time) + " " + url.split('/')[2] + " items: " + str(len(resp_json)))
    return resp_json

def get_data_withings(url, headers):
    start_time = arrow.utcnow()
    resp_json = requests.get(url=url, headers=headers).json()
    finish_time = arrow.utcnow()
    resp_json = resp_json['body']['measuregrps']
    print(str(finish_time - start_time) + " " + url.split('/')[2] + " items: " + str(len(resp_json)))
    return resp_json

def get_step_data_fitbit(url, headers):
    start_time = arrow.utcnow()
    resp_json = requests.get(url,headers=headers).json()
    resp_json = resp_json['activities-steps']
    finish_time = arrow.utcnow()
    print(str(finish_time - start_time) + " " + url.split('/')[2] + " items: " + str(len(resp_json)))
    return resp_json

def epoch_to_local_time(epoch_time):
    date = datetime.datetime.fromtimestamp(epoch_time).strftime('%d-%m-%Y')
    return date

def epoch_to_ordinal(epoch_time):
    ordinal = date.toordinal(datetime.datetime.fromtimestamp(epoch_time))
    return ordinal

def ordinal_to_str(ordinal):
    date_str = date.fromordinal(ordinal).strftime('%d-%m-%Y')
    return date_str

def local_date_str_to_epoch(strdate, date_string):
    datetime_object = datetime.datetime.strptime(strdate, date_string)
    timestamp = datetime.datetime.timestamp(datetime_object)
    return timestamp

def local_date_str_to_ordinal(strdate, date_string):
    datetime_object = datetime.datetime.strptime(strdate, date_string).date()
    ordinal = date.toordinal(datetime_object)
    return ordinal


def main():
    #main_page()
    app.run()


class OneDay(object):
    def __init__(self, 
        date = date.toordinal(datetime.datetime.now()), 
        bodyweight = 0.0, 
        calories = 0, 
        protein = 0, 
        fats = 0, 
        carbs = 0,
        strava_activities = [], 
        liftmuch=False,
        steps = 0
        ):

        self.date = date
        self.bodyweight = bodyweight # in kg, first of day
        self.calories = calories
        self.protein = protein
        self.fats = fats
        self.carbs = carbs
        self.strava_activities = []
        self.liftmuch = liftmuch
        self.steps = steps

    def __repr__(self):
        return (week_day[convert_ord_to_day_of_week(self.date)] + " " + ordinal_to_str(self.date) + " "
            + 'bw: ' + str(self.bodyweight) + " " 
            + 'calories: ' + str(self.calories) + " " 
            + 'steps: ' + str(self.steps) + " " 
            + "strava_count: " + str(len(self.strava_activities))
            )

class StravaActivity(object):
    def __init__(self, 
        strava_date = date.toordinal(datetime.datetime.now()), 
        strava_description = "default_strava", 
        strava_distance=0,
        strava_time=0,
        strava_type="default",
        ):

        self.strava_date = strava_date
        self.strava_description = strava_description
        self.strava_distance = strava_distance # in metres
        self.strava_time = strava_time # in seconds
        self.strava_type = strava_type

    def __repr__(self):
        return ("date: " + str(self.strava_date) + ' ' + str(self.strava_description) + " " + 'distance: ' + str(self.strava_distance))


if __name__ == '__main__':
    main()