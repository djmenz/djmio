import requests
import arrow
import boto3
import math
import datetime
import json
from datetime import date
import collections
from io import StringIO
from multiprocessing import Process
import jsonpickle

from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import send_file
from flask import jsonify

from requests.auth import HTTPBasicAuth

import djm_utils

week_day = ['M','T','W','T','F','S','S']
week_day_long = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

all_data_memory = []


app = Flask(__name__)

@app.route("/")
def read_from_s3():
    s3 = boto3.client('s3')
    s3.download_file('djmio', 'current_full_page_djmio', '/tmp/test_page.html')
    file = open('/tmp/test_page.html', 'r')
    html_string = (file.read())
    file.close()
    return html_string

@app.route("/d")
def read_from_s3_d():
    return redirect(url_for('read_from_s3'))

@app.route("/w")
def read_from_s3weekly():
    s3 = boto3.client('s3')
    s3.download_file('djmio', 'current_weekly_page_djmio', '/tmp/test_page.html')
    file = open('/tmp/test_page.html', 'r')
    html_string = (file.read())
    file.close()
    return html_string

@app.route("/bw")
def read_from_bw_image():
    filename = 'bw_years.png'
    return send_file(filename, cache_timeout=app.config['FILE_DOWNLOAD_CACHE_TIMEOUT'], mimetype='image/gif')

@app.route("/api/daily")
def api_daily():
    start_time = arrow.utcnow()

    allDays = generate_all_days_data()
    
    #Reversing it to make the newest days the lowest array index
    all_days_list = list(allDays)[::-1]

    finish_time = arrow.utcnow()

    print(str(finish_time - start_time) + " " + "Generating api daily")


    return jsonpickle.encode(allDays)

@app.route("/daily_mem")
def daily_mem():
    #import pdb; pdb.set_trace()
    return str(all_data_memory)

@app.route("/daily_mem/<date_url>")
def daily_mem_day(date_url='01-01-2020'):
    #import pdb; pdb.set_trace()
    return str(all_data_memory[djm_utils.local_date_str_to_ordinal(date_url,'%d-%m-%Y')])

@app.route("/daily_gen")
def main_page():

    start_time = arrow.utcnow()

    buf = StringIO()
    buf.write("DJM.IO<br><br>")

    allDays = generate_all_days_data()
    global all_data_memory
    all_data_memory = allDays


    #Reversing it to make the newest days the lowest array index 
    all_days_list = list(allDays)[::-1]

    week_bws = []
    week_steps = []
    week_calories = []
    week_strava_activities = []
    week_lifting = []

    for day in all_days_list:
        
        int_day = djm_utils.convert_ord_to_day_of_week(allDays[day].date)

        if (float(allDays[day].bodyweight) > float(0.0)):
            week_bws.append(float(allDays[day].bodyweight))

        if (int(allDays[day].steps) > 50): #50 steps if i used the fitbit 
            week_steps.append(float(allDays[day].steps))

        if (float(allDays[day].calories) > 0): #50 steps if i used the fitbit 
            week_calories.append(float(allDays[day].calories))

        if len(allDays[day].strava_activities) > 0:
            for strava_activity in allDays[day].strava_activities:
                week_strava_activities.append(strava_activity)

        if len(allDays[day].lifting_sessions) > 0:
            for lifting_session in allDays[day].lifting_sessions:
                week_lifting.append(lifting_session)

        buf.write(str(allDays[day]) + '<br>')
        if (int_day == 0):
            week_avg_bw = 0.0
            week_avg_steps = 0
            week_avg_calories = 0.0

            if ((len(week_bws)) > 0):
                week_avg_bw = sum(week_bws) / len(week_bws)

            if ((len(week_steps)) > 0):
                week_avg_steps = sum(week_steps) / len(week_steps)

            if ((len(week_calories)) > 0):
                week_avg_calories = sum(week_calories) / len(week_calories)

            buf.write("---Stats<br>")
            buf.write("Week average BW: " + ("{:.2f}".format(week_avg_bw)) + 'kg<br>')
            buf.write("Week average steps: " + ("{:.0f}".format(week_avg_steps)) + '<br>')
            buf.write("Week average cals: " + ("{:.0f}".format(week_avg_calories)) + ' ({}/7)'.format(len(week_calories))+ '<br>')
            
            if len(week_strava_activities) > 0:
                buf.write("---Strava Activities<br>")
            
            for strava_activity in week_strava_activities:
                act_day = week_day_long[djm_utils.convert_ord_to_day_of_week(djm_utils.local_date_str_to_ordinal(strava_activity.strava_date, '%Y-%m-%dT%H:%M:%SZ'))]
                pace = strava_activity.strava_time / 60 / strava_activity.strava_distance * 1000
                pace_seconds = (pace % 1) * 60
                pace_seconds_str = ("{:.0f}".format(pace_seconds))
                pace_seconds_str = pace_seconds_str.zfill(2)

                buf.write(act_day + ': ' 
                                  + str(strava_activity.strava_type) + " - "
                                  + str(strava_activity.strava_description) + " "
                                  + "{:.2f}".format(strava_activity.strava_distance/1000) + "km "
                                  + str(datetime.timedelta(seconds=strava_activity.strava_time)) + ' - '
                                  + str(int(pace)) + ':' + pace_seconds_str + ' /km' '<br>')

            if len(week_lifting) > 0:
                buf.write("---Lifting Sessions<br>")

            for lifting_session in week_lifting:
                session_day = week_day_long[djm_utils.convert_ord_to_day_of_week(djm_utils.local_date_str_to_ordinal(lifting_session.lifting_date, '%Y-%m-%d'))] 
                buf.write(session_day + " - " + lifting_session.lifting_description + '<br>')

            buf.write('<br>')

            week_bws = []
            week_steps = []
            week_calories = []
            week_strava_activities = []
            week_lifting = []


    finish_time = arrow.utcnow()

    # duplicate for weekly etc
    save_html_to_s3(buf.getvalue(),'current_full_page_djmio')

    print(str(finish_time - start_time) + " " + "Whole Page Generation")

    return buf.getvalue()


@app.route("/weekly_gen")
def weekly_page():
    buf = StringIO()
    buf.write("DJM.IO<br><br>")

    allDays = generate_all_days_data()
    
    #Reversing it to make the newest days the lowest array index
    all_days_list = list(allDays)[::-1]

    week_bws = []
    week_steps = []
    week_calories = []
    num_liftingsessions = 0
    duration_liftingsessions = 0
    num_strava = 0
    strava_dist_running = 0
    strava_dist_riding = 0

    for day in all_days_list:
        
        int_day = djm_utils.convert_ord_to_day_of_week(allDays[day].date)

        if (float(allDays[day].bodyweight) > float(0.0)):
            week_bws.append(float(allDays[day].bodyweight))

        if (int(allDays[day].steps) > 50): #50 steps if i used the fitbit 
            week_steps.append(float(allDays[day].steps))

        if (float(allDays[day].calories) > 0): #50 steps if i used the fitbit 
            week_calories.append(float(allDays[day].calories))

        # Counting Strava and Lifting sessions
        if len(allDays[day].lifting_sessions) > 0:
            for lifting_session in (allDays[day].lifting_sessions):
                duration_liftingsessions += lifting_session.lifting_duration
            num_liftingsessions += len(allDays[day].lifting_sessions)

        if len(allDays[day].strava_activities) > 0:
            for strava_activity in (allDays[day].strava_activities):
                if strava_activity.strava_type == 'Run':
                    strava_dist_running += strava_activity.strava_distance
                if strava_activity.strava_type == 'Ride':
                    strava_dist_riding += strava_activity.strava_distance

            num_strava += len(allDays[day].strava_activities) 

        #buf.write(str(allDays[day]) + '<br>')
        if (int_day == 0):
            buf.write(str(allDays[day])[0:12] + ' - ')
            week_avg_bw = 0.0
            week_avg_steps = 0
            week_avg_calories = 0.0

            if ((len(week_bws)) > 0):
                week_avg_bw = sum(week_bws) / len(week_bws)

            if ((len(week_steps)) > 0):
                week_avg_steps = sum(week_steps) / len(week_steps)

            if ((len(week_calories)) > 0):
                week_avg_calories = sum(week_calories) / len(week_calories)

            buf.write("Avg BW: " + ("{:.2f}".format(week_avg_bw)) + 'kg - ')
            buf.write("Avg steps: " + ("{:.0f}".format(week_avg_steps)) + ' - ')
            buf.write("Avg cals: " + ("{:.0f}".format(week_avg_calories)) + ' ({}/7)'.format(len(week_calories)) + ' ')
            buf.write("L:" + str(num_liftingsessions) + ' (' + djm_utils.convert_mins_to_hrmins_str(duration_liftingsessions) + ') ')
            buf.write("S:" + str(num_strava) + " (Run " + "{:.1f}".format(strava_dist_running/1000) 
                           + "km " + " Ride " + "{:.1f}".format(strava_dist_riding/1000) + "km " + ")")
            buf.write('<br>')

            week_bws = []
            week_steps = []
            week_calories = []
            num_liftingsessions = 0
            duration_liftingsessions= 0
            num_strava = 0
            strava_dist_running = 0
            strava_dist_riding = 0

    save_html_to_s3(buf.getvalue(),'current_weekly_page_djmio')

    return buf.getvalue()

#import pdb; pdb.set_trace() 

def generate_all_days_data():

    allDays = collections.OrderedDict()

    # Get all the user data from each service
    refresh_token_misc('withings')
    refresh_token_misc('strava')
    refresh_token_misc('fitbit')
    
    auth_urls = get_user_data()

    try:
        #data_strava = []
        data_strava = get_data_from_site(auth_urls['strava']['url'] + auth_urls['strava']['access_token'])
    except:
        data_strava = []

    try:
        if (data_strava['message'] == 'Authorization Error'):
            data_strava = []
    except:
        pass

    #try:
    #    data_tye = get_data_from_site(auth_urls['tye']['url'])[::-1]
    #except:
    data_tye = []
    
    try:
        data_withings = get_data_withings(auth_urls['withings']['url'], {"Authorization": "Bearer {}".format(auth_urls['withings']['access_token'])})
    except:
        data_withings = []

    try:
        data_fitbit_step = get_step_data_fitbit(auth_urls['fitbit']['url'], {"Authorization": "Bearer {}".format(auth_urls['fitbit']['access_token'])})[::-1]
    except:
        data_fitbit_step = []

    try:
        data_liftmuch = get_liftmuch_data()    
    except:
        data_liftmuch = []

    #data_fitbit_hr = get_hr_data_fitbit()
    #data_fitbit_sleep = get_hr_data_sleep()
    start_time = arrow.utcnow()
    
    #First day of 2018 
    earliest_date = djm_utils.local_date_str_to_ordinal('01-01-2018', '%d-%m-%Y')
    todays_date_epoch = int(datetime.datetime.now().timestamp())
    todays_date = date.toordinal(datetime.datetime.fromtimestamp(todays_date_epoch))

    for day in range(earliest_date,todays_date+1):
        
        tempday = OneDay()
        tempday.date = day
        allDays[day]= tempday

    # populate strava data
    for date_entry in data_strava:
        this_day =  djm_utils.epoch_to_ordinal(djm_utils.local_date_str_to_epoch(date_entry['start_date_local'],'%Y-%m-%dT%H:%M:%SZ'))
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
        this_day = djm_utils.local_date_str_to_ordinal(data_entry['date'], '%Y-%m-%d')
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
        this_day = djm_utils.epoch_to_ordinal(data_entry['date'])
        try:
            t_weight = data_entry['measures'][0]['value']
            t_unit = data_entry['measures'][0]['unit']
            t_date = data_entry['date']
            t_date_human = djm_utils.epoch_to_local_time(t_date)
            tempweight = ("%.2f" % (t_weight/math.pow(10,-t_unit)))
            allDays[this_day].bodyweight = tempweight
        except KeyError:
            #print('key error withings')
            continue   

    #populate fitbit-step data
    for data_entry in data_fitbit_step:
        this_day = djm_utils.local_date_str_to_ordinal(data_entry['dateTime'], '%Y-%m-%d')
        try:
            temp_steps = data_entry['value']
            allDays[this_day].steps = temp_steps
        except KeyError:
            print('key error fitbit steps')
            continue  

    #Populate liftmuch data - currently won't list entries without a time listed
    try:
        data_liftmuch = data_liftmuch['workouts']
    except:
        data_liftmuch = []


    for data_entry in data_liftmuch:
        this_day = djm_utils.local_date_str_to_ordinal(data_entry['date'], '%Y-%m-%d')

        # If time isn't in format 'xyz Time x:xx; set it to default 60 minutes
        sess_time_mins = 60
        sess_description = "No details"

        try:
            time_str = data_entry['extra_info']['notes'].split('Time')[-1].strip()
            sess_time_mins = (int(time_str.split(':')[0]) * 60) + int(time_str.split(':')[1])        
        except Exception as e:
            pass        
        
        try:
            sess_description = data_entry['extra_info']['notes']        
        except Exception as e:
            pass        

        # Convert liftmuch date to allDay's date
        try:
            temp_liftmuch_session = LiftingSession(data_entry['date'], sess_description, sess_time_mins)
            allDays[this_day].lifting_sessions.append(temp_liftmuch_session)
        except Exception as e:
            #print(data_entry['date'])
            #print('date not in bounds of display\n ')
            continue

    finish_time = arrow.utcnow()
    print(str(finish_time - start_time) + " consolidating all data" )
    return allDays

def get_user_data():
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
    table = dynamodb.Table('djmio_platform_urls')
    peak_response = table.scan()

    platform_auth = {}
    for row in peak_response['Items']:
        platform_auth[row['platform']] = row

    return(platform_auth)


def refresh_token_misc(platform):
    start_time_token = arrow.utcnow()
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
    table = dynamodb.Table('djmio_platform_urls')
    auth_urls = get_user_data()
    
    #this can be removed when its a database patch call
    url = auth_urls[platform]['url_refresh_token']
    url_api = auth_urls[platform]['url']
    client_id = auth_urls[platform]['client_id']
    client_secret = auth_urls[platform]['client_secret']

    refresh_token = auth_urls[platform]['refresh_token']

    if platform == 'fitbit':
        headers = HTTPBasicAuth(client_id, client_secret)
        data = {'grant_type': 'refresh_token', 'refresh_token': refresh_token }
        resp_json = requests.post(url=url, auth=HTTPBasicAuth(client_id, client_secret), data=data).json()
    else:
        data = {'client_id': client_id, 'grant_type': 'refresh_token', 'client_secret': client_secret, 'refresh_token': refresh_token }
        resp_json = requests.post(url=url, data=data).json()

    finish_time_token = arrow.utcnow()
    print(str(finish_time_token - start_time_token) + " " + platform + " token refreshed")

    # Change to patch just these 2 attributes, then don't need to store above:
    # - refresh_token
    # - access_token
    table.put_item(
                    Item={
                        'platform': platform,
                        'refresh_token': resp_json['refresh_token'],
                        'access_token': resp_json['access_token'],
                        'url_refresh_token': url,
                        'url': url_api,
                        'client_id': client_id,
                        'client_secret': client_secret,
                    },
                )

    # response = table.update_item(
    #     Key={
    #         'url_link': row['url_link'],
    #     },
    #     UpdateExpression="set notified = :r",
    #     ExpressionAttributeValues={
    #         ':r': 'true',
    #     },
    #     ReturnValues="UPDATED_NEW"
    #     )

    # response = table.update_item(
    #     Key={
    #         'url_link': row['url_link'],
    #     },
    #     UpdateExpression="set notified = :r",
    #     ExpressionAttributeValues={
    #         ':r': 'true',
    #     },
    #     ReturnValues="UPDATED_NEW"
    #     )finish_time = arrow.utcnow()
    return

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

# Test function retrieving static version from S3 - will be replaced with proper copy later
def get_liftmuch_data():
    s3 = boto3.client('s3')
    s3.download_file('djmio', 'sept15_liftmuch.json', '/tmp/liftmuch.json')
    file = open('/tmp/liftmuch.json', 'r')
    resp_json = json.load(file)
    file.close()
    return resp_json

def save_html_to_s3(full_html_page, object_name):
    s3 = boto3.resource('s3')
    s3.Bucket('djmio').put_object(Key=object_name, Body=full_html_page)

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
        lifting_sessions = [],
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
        self.lifting_sessions = []
        self.liftmuch = liftmuch
        self.steps = steps

    def __repr__(self):
        return (week_day[djm_utils.convert_ord_to_day_of_week(self.date)] + " " + djm_utils.ordinal_to_str(self.date) + " "
            + 'bw: ' + str(self.bodyweight) + " " 
            + 'cals: ' + str(self.calories) + " " 
            + 'P: ' + str(self.protein) + " "
            + 'C: ' + str(self.carbs) + " "
            + 'F: ' + str(self.fats) + " "
            + 'steps: ' + str(self.steps)
            )

class LiftingSession(object):
    def __init__(self, 
        lifting_date = date.toordinal(datetime.datetime.now()), 
        lifting_description = "default_lifts",
        lifting_duration = 0 #minutes 
        ):

        self.lifting_date = lifting_date
        self.lifting_description = lifting_description
        self.lifting_duration = lifting_duration

    def __repr__(self):
        return ("date: " + str(self.lifting_date) + ' ' + str(self.lifting_description))


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
    main_page() #737507, M 23-03-2020
    main()