from bs4 import BeautifulSoup
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

from waitress import serve

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

week_day = ['M','T','W','T','F','S','S']
week_day_long = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']


# Go to all the endpoints, saves the resultant data into a json file on S3

def generate_all_days_data(archive=False):

    allDays = collections.OrderedDict()

    # Get all the user data from each service
    refresh_token_withings()
    refresh_token_misc('strava')
    refresh_token_misc('fitbit')
    
    auth_urls = get_user_data()

    try:
        page_num = 1
        still_data = True
        data_strava = []
        while still_data:
            data_strava_one_page = get_data_from_site(auth_urls['strava']['url'] + auth_urls['strava']['access_token'] + '&per_page=200&page=' + str(page_num))
            
            if ('message' in data_strava_one_page and data_strava_one_page['message'] == 'Authorization Error'):
                break
        
            data_strava.extend(data_strava_one_page)
            page_num +=1
            if len(data_strava_one_page) == 0:
                still_data = False
    except:
        data_strava = []
   
    try:
        if (data_strava['message'] == 'Authorization Error'):
            data_strava = []
    except:
        pass

    try:
        #retrieve archived data from old site
        data_tye1_archive = []
        s3 = boto3.client('s3')
        s3.download_file('djmio', 'tye1_archive_2015-Aug2021.json', '/tmp/tye1_archive_2015-Aug2021.json')
        file = open('/tmp/tye1_archive_2015-Aug2021.json', 'r')
        data_tye1_archive = json.loads(file.read())[::-1] # the reversing doesn't actually matter since it gets put into a date dict later
        file.close()
        
        #retrieve data from new tye site - temporary empty until the API is working the same
        data_tye_new = []
        data_tye_new = get_data_from_tye2(auth_urls['tye']['url'], auth_urls['tye']['username'], auth_urls['tye']['password'])

        # Consolidate
        data_tye = data_tye1_archive + data_tye_new

    except:
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
        data_liftmuch = get_liftmuch_data(auth_urls['liftmuch'])    
    except:
        data_liftmuch = []

    # Saving the raw data from all the api endpoints
    if archive:
        consolidated_data = {
            'strava': data_strava,
            'tye': data_tye,
            'withings': data_withings,
            'fitbit_step': data_fitbit_step,
            'liftmuch': data_liftmuch
        }

        with open("raw_data_archive.json", 'w') as file:
            file.write(jsonpickle.encode(consolidated_data))

        t = datetime.datetime.now()
        file_name = str(t.year) + "_" + str(t.month) + "_" + str(t.day) + "_" + "raw_data_archive.json"
        s3 = boto3.resource('s3')
        s3.Bucket('djmio').put_object(Key=file_name, Body=open("raw_data_archive.json",'rb'))

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
            strava_time=date_entry['elapsed_time'], #moving_time' vs 'elapsed_time':
            strava_moving_time=date_entry['moving_time'],
            strava_type=date_entry['type'],
            strava_raw=date_entry
        )

        try:
            #print(temp_strava_activity)
            allDays[this_day].strava_activities.append(temp_strava_activity.__dict__)
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
            allDays[this_day].fats = data_entry['fats']
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

    #Populate liftmuch data
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

        try:
            sess_exercises = data_entry['exercises']       
        except Exception as e:
            print(e)
            pass                

        # Convert liftmuch date to allDay's date
        try:
            temp_liftmuch_session = LiftingSession(data_entry['date'], sess_description, sess_time_mins, sess_exercises)
            allDays[this_day].lifting_sessions.append(temp_liftmuch_session.__dict__)
        except Exception as e:
            #print(data_entry['date'])
            #print('date not in bounds of display\n ')
            continue

    res_dict = collections.OrderedDict()

    # at this point we have an ordered dictionary of OneDay objects that we need to dump to json, so need to convert day object to json
    for day in allDays.keys():
        date_string = djm_utils.ordinal_to_str_iso(day)
        res_dict[date_string] = allDays[day].__dict__


    finish_time = arrow.utcnow()
    print(str(finish_time - start_time) + " consolidating all data" )

    # Save all days data as serialised object to S3
    with open("latest_all_days.json", 'w') as file:
        file.write(json.dumps((res_dict)))

    s3 = boto3.resource('s3')
    s3.Bucket('djmio').put_object(Key="latest_all_days.json", Body=open("latest_all_days.json",'rb'))

    return

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

    return

def refresh_token_withings():
    platform = 'withings'
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

    data = {'client_id': client_id, 
            'grant_type': 'refresh_token', 
            'client_secret': client_secret, 
            'refresh_token': refresh_token, 
            'action': 'requesttoken' 
            }
    resp_json = requests.post(url=url, data=data).json()

    finish_time_token = arrow.utcnow()
    print(str(finish_time_token - start_time_token) + " " + platform + " token refreshed")
    
    # Change to patch just these 2 attributes, then don't need to store above:
    # - refresh_token
    # - access_token
    table.put_item(
                    Item={
                        'platform': platform,
                        'refresh_token': resp_json['body']['refresh_token'],
                        'access_token': resp_json['body']['access_token'],
                        'url_refresh_token': url,
                        'url': url_api,
                        'client_id': client_id,
                        'client_secret': client_secret,
                    },
                )

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

def get_data_from_tye2(base_url, username, pwd):
    start_time = arrow.utcnow()

    data_auth = {
        "username": username,
        "password" : pwd
    }

    auth_url = base_url + '/token'    
    auth_headers = {'content-type': 'application/x-www-form-urlencoded'}
    res = requests.post(url = auth_url, headers=auth_headers, data=data_auth)
    access_token = res.json()['access_token']
        
    get_headers ={'Content-Type':'application/json', 'Authorization': 'Bearer {}'.format(access_token)}
    tracking_get_url = base_url + '/api/trackingmerged'
    res_data = requests.get(tracking_get_url, headers=get_headers)
    res_json = res_data.json()

    res_dict = {}

    # Converting list of individual items to day summaries
    for item in res_json:
        if item['date'] in res_dict:
            temp_culm = res_dict[item['date']]
            res_dict[item['date']] = {
                'fats' : temp_culm['fats'] + (item['fats'] * item['quantity']),
                'protein' : temp_culm['protein'] + (item['protein']  * item['quantity']),
                'carbs' : temp_culm['carbs'] + (item['carbs']  * item['quantity']),
                'calories' : temp_culm['calories'] + (item['calories']  * item['quantity'])
            }
        else:
            res_dict[item['date']] = {
                'fats' : item['fats'] * item['quantity'],
                'protein' : item['protein']  * item['quantity'],
                'carbs' : item['carbs']  * item['quantity'],
                'calories' : item['calories']  * item['quantity']
                }

    # convert dict to list so it matches
    res_list = []
    for key, values in res_dict.items():
        values['date'] = key
        res_list.append(values)

    finish_time = arrow.utcnow()
    print(str(finish_time - start_time) + " " + base_url + " items: " + str(len(res_list)))
    return res_list

def get_step_data_fitbit(url, headers):
   # need to fix url so its 1095 days before, not hardcoded
    start_time = arrow.utcnow()
    resp_json = requests.get(url,headers=headers).json()
    resp_json = resp_json['activities-steps']
    finish_time = arrow.utcnow()
    print(str(finish_time - start_time) + " " + url.split('/')[2] + " items: " + str(len(resp_json)))
    return resp_json

# Taken from http://www.liftmuch.club/api/v1/workouts after logging in
def get_liftmuch_data(liftmuch_data_dict):
    start_time = arrow.utcnow()

    session_req = requests.Session()

    get_rep = session_req.get(liftmuch_data_dict['url_refresh_token'])
    soup = BeautifulSoup(get_rep.content, 'html.parser')
    csrf_cur = soup.body.input.attrs['value']
   
    payload = {            
            'csrf_token': csrf_cur,
            'next':'/',
            'reg_nex':'/',
            'email': liftmuch_data_dict['username'],
            'password': liftmuch_data_dict['password']
             }

    resp_login = session_req.post(url=liftmuch_data_dict['url_refresh_token'], data=payload)
    resp_json = session_req.get(liftmuch_data_dict['url']).json()

    finish_time = arrow.utcnow()
    print(str(finish_time - start_time) + " " + liftmuch_data_dict['url'].split('/')[2] + " items: " + str(len(resp_json['workouts'])))

    return resp_json

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
            + 'cals: ' + str("{:.2f}".format(self.calories)) + " " 
            + 'P: ' + str("{:.2f}".format(self.protein)) + " "
            + 'C: ' + str("{:.2f}".format(self.carbs)) + " "
            + 'F: ' + str("{:.2f}".format(self.fats)) + " "
            + 'steps: ' + str(self.steps)
            )

class LiftingSession(object):
    def __init__(self, 
        lifting_date = date.toordinal(datetime.datetime.now()), 
        lifting_description = "default_lifts",
        lifting_duration = 0, #minutes 
        lifting_exercises = []
        ):

        self.lifting_date = lifting_date
        self.lifting_description = lifting_description
        self.lifting_duration = lifting_duration
        self.lifting_exercises = lifting_exercises

    def __repr__(self):
        return ("date: " + str(self.lifting_date) + ' ' + str(self.lifting_description))


class StravaActivity(object):
    def __init__(self, 
        strava_date = date.toordinal(datetime.datetime.now()), 
        strava_description = "default_strava", 
        strava_distance=0,
        strava_time=0,        
        strava_moving_time=0,
        strava_type="default",
        strava_raw={}
        ):

        self.strava_date = strava_date
        self.strava_description = strava_description
        self.strava_distance = strava_distance # in metres
        self.strava_time = strava_time # in seconds
        self.strava_moving_time = strava_moving_time # in seconds
        self.strava_type = strava_type
        self.strava_raw = strava_raw

    def __repr__(self):
        return ("date: " + str(self.strava_date) + ' ' 
            + str(self.strava_description) + " " + 'distance: ' + str(self.strava_distance) + ' ' 
            + "time:" + str(self.strava_time)
            )

