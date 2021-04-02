from flask import Flask
import urllib, json
from io import StringIO
import math
from datetime import timedelta
from operator import add
from flask import request
import boto3

from flask import render_template

import datetime

app = Flask(__name__)

@app.route("/")
def hello():
	number_of_days = 270

	WeekDay = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
	buf = StringIO()
	buf2 = StringIO()

	#Get Urls from dynamo
	dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
	table = dynamodb.Table('djmio_platform_urls')

	url_response = table.scan()	
	api_urls = url_response['Items']
	
	api_dict = {}
	for api_url in api_urls:
		api_dict[api_url['platform']] = api_url['url']

	#read_urls_from_file
	url_file = open("url_info.txt","r")

	# Strava
	url_strava = api_dict['strava']
	try:
		response_strava = urllib.request.urlopen(url_strava)
		data_strava = json.loads(response_strava.read())
		print(data_strava)
	except:
		data_strava = ""
	
	# Nokia
	url_nokia = api_dict['nokiahealth']
	try:
		response = urllib.request.urlopen(url_nokia)
		data = json.loads(response.read())
	except:
		data = ""

	# trackyoureating
	start_tye_url = datetime.datetime.fromordinal(((datetime.date.today().toordinal()) - number_of_days)).strftime("%Y%m%d")
	url_tye = api_dict['tye']+start_tye_url
	response_tye = urllib.request.urlopen(url_tye)
	try:
		data_tye = json.loads(response_tye.read())
	except:
		pass

	#close file
	url_file.close()

	# # Read in liftmuch data from manual file download
	# data_liftmuch = []

	# try:
	# 	with open ("workout_page_source.html", "r") as myfile:
	# 		data_lm=myfile.readlines()

	# 	for line in data_lm:
	# 		dates = line.strip()
	# 		if dates.startswith('<small class="hidden-xs hidden-sm">'):
	# 			t = (dates.split('>')[1].split('<')[0]).replace("  "," ")
	# 			t_date = t.split(" ")[2] + "-" + t[:3] + "-" + t.split(" ")[1].strip(',')
	# 			t_day = datetime.datetime.strptime(t_date, '%Y-%b-%d').date().toordinal()
	# 			data_liftmuch.append(t_day)
	# except Exception:
	# 	pass

	#get data for the last number_of_days days. note alldays array[startdate(0) to endate[number_of_days]]
	allDays = []
	startdate = (datetime.date.today().toordinal()) - number_of_days
	enddate = datetime.date.today().toordinal()

	# Populate the dates
	for x in range(startdate,enddate+1):
		tempday = OneDayData()
		tempday.date = x
		allDays.append(tempday)

	# Populate the bodyweights
	try:
		for x in range(0,len(data['body']['measuregrps'])-1):
			t_date = data['body']['measuregrps'][x]['date']
			t_weight = data['body']['measuregrps'][x]['measures'][0]['value']
			t_unit = data['body']['measuregrps'][x]['measures'][0]['unit']
			t_date = data['body']['measuregrps'][x]['date']
			tempweight = ("%.2f" % (t_weight/math.pow(10,-t_unit)))
			tempdate = datetime.datetime.fromtimestamp(t_date).date().toordinal()-startdate
			if (tempdate >= 0):
				allDays[tempdate].bodyweight = tempweight
	except Exception:
		pass

	# Populate the calories information
	try:
		for x in range(len(data_tye)-1,-1,-1):
			tempStartDate = datetime.datetime.strptime(data_tye[x]['date'], '%Y-%m-%d').date().toordinal()-startdate
			allDays[tempStartDate].calories = data_tye[x]['calories']
			allDays[tempStartDate].protein = data_tye[x]['protein']
			allDays[tempStartDate].fat = data_tye[x]['fats']
			allDays[tempStartDate].carbs = data_tye[x]['carbs']

			buf.write("Calories:" + str(data_tye[x]['calories']) + "<br>")
			buf.write("Protein:" + str(data_tye[x]['protein']) + "<br>")
			buf.write("Carbs:" + str(data_tye[x]['carbs']) + "<br>")
			buf.write("Fat:" + str(data_tye[x]['fats']) + "<br>")
	except:
		pass


	# Populate strava data
	try: 
		for x in range(0,len(data_strava)):
			tempDate = datetime.datetime.strptime(str(data_strava[x]['start_date_local'].split("T")[0]), '%Y-%m-%d').date().toordinal()-startdate
			if(tempDate >= 0):
				allDays[tempDate].strava_description = data_strava[x]['name']
				allDays[tempDate].strava_distance = int(data_strava[x]['distance'])
				allDays[tempDate].strava_time = data_strava[x]['elapsed_time']
				allDays[tempDate].strava_type = data_strava[x]['type']
	except:
		pass
		

	# Populate the liftmuch data from from manual file download
	#for x in range(0,len(data_liftmuch)):
	#	if (data_liftmuch[x]-startdate > -1):
	#		allDays[data_liftmuch[x]-startdate].liftmuch = True


	# Print each day
	buf2.write("DJM.IO<br><br>")

	# add button

	weekly_food = [0,0,0,0]
	weekly_count_food = 0;

	weekly_bodyweight = 0.0
	weekly_count_bodyweight = 0;

	weekly_strava_actions = 0;

	weekly_lifting_sessions = 0;

	for x in range (len(allDays) -1,-1,-1):
		if (request.args.get('average') != "yes"):
			buf2.write(str(datetime.date.fromordinal(allDays[x].date)))
			buf2.write(" " + WeekDay[datetime.date.fromordinal(allDays[x].date).weekday()])
			buf2.write("<br>")
			buf2.write(str(allDays[x].bodyweight) + "kg" + "<br>")
			buf2.write("Calories: " + str(allDays[x].calories) + "<br>")
			buf2.write("Protein: " + str(allDays[x].protein) + "<br>")
			buf2.write("Fat: " + str(allDays[x].fat) + "<br>")
			buf2.write("Carbs: " + str(allDays[x].carbs) + "<br>")

			if (allDays[x].liftmuch == True):
				buf2.write("@Lifting Session<br>")

			if (allDays[x].strava_description != 'default_strava'):
				buf2.write("# " + str(allDays[x].strava_description) + "<br>")
				buf2.write("Type: " + str(allDays[x].strava_type) + "<br>")
				buf2.write("- " + str(allDays[x].strava_distance/1000) + "." + str(allDays[x].strava_distance%1000) + "km" + "<br>")
				buf2.write("- " +  str(allDays[x].strava_time/60) + ":" + str(allDays[x].strava_time%60) + "<br>")

				#Calculate and show minutes per km
				total_component = ((allDays[x].strava_time/float(allDays[x].strava_distance)/.06))
				min_component = int(total_component)
				sec_component = int((total_component % 1) * 60)

				buf2.write("- " + str(min_component) + ":" + str(sec_component) + "min/km" + "<br>")

			buf2.write("<br>")

		else:
			if (datetime.date.fromordinal(allDays[x].date).weekday() == 6):
				buf2.write(datetime.date.fromordinal(allDays[x].date))
				buf2.write(" " + WeekDay[datetime.date.fromordinal(allDays[x].date).weekday()] + " | ")

		if (float(allDays[x].bodyweight) > 0.0):
			weekly_count_bodyweight = weekly_count_bodyweight + 1
			weekly_bodyweight += float(allDays[x].bodyweight)

		if (allDays[x].calories) > 0:
			weekly_count_food = weekly_count_food + 1
			weekly_food = map(add,weekly_food,[allDays[x].calories,allDays[x].protein,allDays[x].fat,allDays[x].carbs])

		if (allDays[x].strava_description != 'default_strava'):
			weekly_strava_actions = weekly_strava_actions + 1;

		if (allDays[x].liftmuch == True):
			weekly_lifting_sessions = weekly_lifting_sessions + 1;

		if ((datetime.date.fromordinal(allDays[x].date).weekday()) == 0):
			average_bodyweight = 0.0
			if (weekly_count_bodyweight > 0):
				average_bodyweight = weekly_bodyweight / weekly_count_bodyweight

			average_food = [0,0,0,0]
			if (weekly_count_food > 0):
				average_food = [x / float(weekly_count_food) for x in weekly_food]

			buf2.write("Average: BW(" + str(weekly_count_bodyweight)  + ")= " + str("%.2f" % average_bodyweight)+ " | ")
			buf2.write("Calories(" + str(weekly_count_food)  + ") = " + str(int(average_food[0]))+ " | ")
			buf2.write("Protein = " + str('%10s' % int(average_food[1]))+ " | ")
			buf2.write("Fat = " + str(int(average_food[2])) + " | ")
			buf2.write("Carbs = " + str(int(average_food[3])) + " | ")
			buf2.write("Lifts = " + str(weekly_lifting_sessions) + " | ")
			buf2.write("Strava count = " + str(weekly_strava_actions) + "<br>")

			if (request.args.get('average') != "yes"):
				buf2.write("------------------------------<br>")
			
			# re init weekly counts
			weekly_bodyweight = 0.0
			weekly_count_bodyweight = 0;

			weekly_food = [0,0,0,0]
			weekly_count_food = 0;

			weekly_strava_actions = 0;

			weekly_lifting_sessions = 0;


	# Return a template with all the correct data
	return buf2.getvalue()


class OneDayData(object):
	def __init__(self, date=datetime.datetime.today(), bodyweight = 0.0, calories = 0, protein =0, fat =0, carbs =0,
     strava_description = "default_strava", strava_distance=0,strava_time=0,strava_type="default",liftmuch=False):
		self.date = date

		self.bodyweight = bodyweight # in kg

		self.calories = calories
		self.protein = protein
		self.fat = fat
		self.carbs = carbs

		self.strava_description = strava_description
		self.strava_distance = strava_distance # in metres
		self.strava_time = strava_time # in seconds
		self.strava_type = strava_type

		self.liftmuch = liftmuch




#export FLASK_APP=test.py
#flask run
	
