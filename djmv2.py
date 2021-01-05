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
import sys

from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import send_file
from flask import jsonify

from requests.auth import HTTPBasicAuth
from flask_cors import CORS
import djm_utils
import djm_refresh

# configuration
DEBUG = True

# instantiate the app
app = Flask(__name__)
app.config.from_object(__name__)

# enable CORS
CORS(app)

week_day = ['M','T','W','T','F','S','S']
week_day_long = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

all_data_memory = []
all_data_memory_summary = ""


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

# this should be changed to read from memory if present
@app.route("/api")
def daily_mem():
    #import pdb; pdb.set_trace()
    return str(load_all_days_data_from_s3_file())

@app.route("/api/daily")
def api_daily():
    start_time = arrow.utcnow()
    allDays = load_all_days_data_from_s3_file()
    
    #Reversing it to make the newest days the lowest array index
    all_days_list = list(allDays)[::-1]

    finish_time = arrow.utcnow()

    print(str(finish_time - start_time) + " " + "Generating api daily")

    return jsonpickle.encode(allDays)

# Return the given date + 6 days of data
@app.route("/api/daily/<date_url>")
def daily_mem_day(date_url='01-01-2020'):
    #import pdb; pdb.set_trace()
    chosen_date_ord = djm_utils.local_date_str_to_ordinal(date_url,'%d-%m-%Y')
    ordinals = []
    for x in range(0,7):
        ordinals.append(chosen_date_ord + x)

    return_data = []
    for ordinal in ordinals:
        if (ordinal in all_data_memory): 

            date_day_of_week = week_day_long[djm_utils.convert_ord_to_day_of_week(all_data_memory[ordinal].date)]

            return_data.append({
                "date": f"{date_day_of_week} {djm_utils.ordinal_to_str(all_data_memory[ordinal].date)}",
                "bodyweight": all_data_memory[ordinal].bodyweight,
                "steps": all_data_memory[ordinal].steps,
                "calories": all_data_memory[ordinal].calories,
                "lifting_sessions": all_data_memory[ordinal].lifting_sessions,
                "strava_sessions": all_data_memory[ordinal].strava_activities
                })
        else:
            date_day_of_week = week_day_long[djm_utils.convert_ord_to_day_of_week(ordinal)]
            return_data.append({
                "date": f"{date_day_of_week} {djm_utils.ordinal_to_str(ordinal)}",
                "bodyweight": 0,
                "steps": 0,
                "calories": 0,
                "lifting_sessions": [],
                "strava_sessions": []                
                })
    return jsonpickle.encode(return_data)

@app.route("/api/summary")
def summary_mem():
    #import pdb; pdb.set_trace()

    return all_data_memory_summary
    #return jsonpickle.encode(all_data_memory_summary.split("<br>"))

# Convert the raw day data into a html page
@app.route("/daily_gen")
def daily_page():

    today = datetime.datetime.now()
    today_str = "date"
    today_str = f"{today.hour}:{today.minute} {today.day}/{today.month}/{today.year}"

    start_time = arrow.utcnow()

    buf = StringIO()
    #buf.write(f"DJM.IO {today_str} <br><br>")
    buf.write(f"DJM.IO <br>")
    buf.write(f"<a href=/w>weekly view</a><br><br>")

    allDays = load_all_days_data_from_s3_file()
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
                #print(strava_activity)

                act_day = week_day_long[djm_utils.convert_ord_to_day_of_week(djm_utils.local_date_str_to_ordinal(strava_activity.strava_date, '%Y-%m-%dT%H:%M:%SZ'))]
                
                if strava_activity.strava_type == 'Run':
                    pace = strava_activity.strava_time / 60 / strava_activity.strava_distance * 1000
                    pace_seconds = (pace % 1) * 60
                    pace_seconds_str = ("{:.0f}".format(pace_seconds))
                    pace_seconds_str = pace_seconds_str.zfill(2)
                    pace_details = str(int(pace)) + ':' + pace_seconds_str + ' mins/km'
                if strava_activity.strava_type == 'Ride':

                    pace_details = "{:.2f}".format(((strava_activity.strava_distance/1000) / (strava_activity.strava_time/3600))) + " km/hr"

                buf.write(act_day + ': ' 
                                  + str(strava_activity.strava_type) + " - "
                                  + str(strava_activity.strava_description) + " "
                                  + "{:.2f}".format(strava_activity.strava_distance/1000) + "km "
                                  + str(datetime.timedelta(seconds=strava_activity.strava_time)) + ' - '
                                  + pace_details + '<br>')

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
    buf.write(f"<a href=/d>daily view</a><br><br>")
    global all_data_memory_summary
    allDays = load_all_days_data_from_s3_file()
    
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

    all_data_memory_summary = buf.getvalue()
    save_html_to_s3(buf.getvalue(),'current_weekly_page_djmio')

    return buf.getvalue()

def load_all_days_data_from_s3_file():
    s3 = boto3.client('s3')
    s3.download_file('djmio', 'latest_all_days_json', '/tmp/allDays.json')
    file = open('/tmp/allDays.json', 'r')
    #import pdb; pdb.set_trace() 
    allDays = jsonpickle.decode(file.read())

    file.close()
    return allDays

@app.route("/regen")
def regenerate_from_s3():
    daily_page()
    weekly_page()
    return redirect(url_for('read_from_s3'))

def save_html_to_s3(full_html_page, object_name):
    s3 = boto3.resource('s3')
    s3.Bucket('djmio').put_object(Key=object_name, Body=full_html_page)

def main():
    if len(sys.argv) == 2:
        if sys.argv[1] == 'refresh':
            djm_refresh.generate_all_days_data()
            daily_page()
            weekly_page()

    #app.run(use_reloader=False)
    else:
        app.run(host='0.0.0.0', port=8080,use_reloader=False)
        #serve(app, host='0.0.0.0', port=80)

if __name__ == '__main__':
    #Generates the main page, and stored the results in memory for return via the API endpoints
    #daily_page() #737507, M 23-03-2020

    main()
