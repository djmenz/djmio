from flask import Flask
import urllib, json
import StringIO
import math
from datetime import timedelta
from operator import add
from flask import request

import datetime
app = Flask(__name__)

@app.route("/")
def hello():
	WeekDay = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
	buf = StringIO.StringIO()
	buf2 = StringIO.StringIO()
    
	#read_urls_from_file
	url_file = open("url_info.txt","r")

	# Strava
	url_strava = url_file.readline()
	response_strava = urllib.urlopen(url_strava)
	data_strava = json.loads(response_strava.read())

	# Nokia
	url_nokia = url_file.readline()
	response = urllib.urlopen(url_nokia)
	data = json.loads(response.read())


	# trackyoureating
	url_tye = url_file.readline()
	response_tye = urllib.urlopen(url_tye)
	data_tye = json.loads(response_tye.read())

	#close file
	url_file.close()

	#get data for the last 90 days
	allDays = []
	startdate = (datetime.date.today().toordinal()) - 90
	enddate = datetime.date.today().toordinal()

	# Populate the dates
	for x in range(startdate,enddate+1):
		tempday = OneDayData()
		tempday.date = x
		allDays.append(tempday)
		#buf2.write(str(allDays[x-startdate].date) + "<br>")

	# Populate the bodyweights
	for x in range(0,len(data['body']['measuregrps'])-1):
		t_date = data['body']['measuregrps'][x]['date']
		t_weight = data['body']['measuregrps'][x]['measures'][0]['value']
		t_unit = data['body']['measuregrps'][x]['measures'][0]['unit']
		t_date = data['body']['measuregrps'][x]['date']
		tempweight = ("%.2f" % (t_weight/math.pow(10,-t_unit)))
		
		allDays[datetime.datetime.fromtimestamp(t_date).date().toordinal()-startdate].bodyweight = tempweight

	# Populate the calories information
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
		
	# Print each day

	weekly_food = [0,0,0,0]
	weekly_count_food = 0;

	weekly_bodyweight = 0.0
	weekly_count_bodyweight = 0;

	for x in range (len(allDays) -1,-1,-1):
		if (request.args.get('average') != "yes"):
			buf2.write(datetime.date.fromordinal(allDays[x].date))
			buf2.write(" " + WeekDay[datetime.date.fromordinal(allDays[x].date).weekday()])
			buf2.write("<br>")
			buf2.write(str(allDays[x].bodyweight) + "kg" + "<br>")
			buf2.write("Calories: " + str(allDays[x].calories) + "<br>")
			buf2.write("Protein: " + str(allDays[x].protein) + "<br>")
			buf2.write("Fat: " + str(allDays[x].fat) + "<br>")
			buf2.write("Carbs: " + str(allDays[x].carbs) + "<br>")
			buf2.write("<br>")

		else:
			if (datetime.date.fromordinal(allDays[x].date).weekday() == 6):
				buf2.write(datetime.date.fromordinal(allDays[x].date))
				buf2.write(" " + WeekDay[datetime.date.fromordinal(allDays[x].date).weekday()])
				buf2.write("<br>")

		if (allDays[x].bodyweight > 0.0):
			weekly_count_bodyweight = weekly_count_bodyweight + 1
			weekly_bodyweight += float(allDays[x].bodyweight)

		if (allDays[x].calories) > 0:
			weekly_count_food = weekly_count_food + 1
			weekly_food = map(add,weekly_food,[allDays[x].calories,allDays[x].protein,allDays[x].fat,allDays[x].carbs])

		if ((datetime.date.fromordinal(allDays[x].date).weekday()) == 0):
			average_bodyweight = 0.0
			if (weekly_count_bodyweight > 0):
				average_bodyweight = weekly_bodyweight / weekly_count_bodyweight

			average_food = [0,0,0,0]
			if (weekly_count_food > 0):
				average_food = [x / float(weekly_count_food) for x in weekly_food]

			buf2.write("<b>Average bodyweight(" + str(weekly_count_bodyweight)  + ")= " + str("%.2f" % average_bodyweight)+ "<br>")
			buf2.write("Average Calories(" + str(weekly_count_food)  + ") = " + str(int(average_food[0]))+ "<br>")
			buf2.write("Average Protein = " + str(int(average_food[1]))+ "<br>")
			buf2.write("Average Fat = " + str(int(average_food[2]))+ "<br>")
			buf2.write("Average Carbs = " + str(int(average_food[3]))+ "</b><br>")
			buf2.write("---------------------<br>")
			
			# re init weekly counts
			weekly_bodyweight = 0.0
			weekly_count_bodyweight = 0;

			weekly_food = [0,0,0,0]
			weekly_count_food = 0;






	# stuff to remove later, for reference only

	start_of_week = datetime.date.fromordinal(datetime.datetime.today().toordinal() - datetime.datetime.today().weekday())

	for x in range(0,7):
		current_day = start_of_week + timedelta(days=x)


		for x in range(0,len(data['body']['measuregrps'])-1):
			t_date = data['body']['measuregrps'][x]['date']
			if (str(datetime.datetime.fromtimestamp(t_date).date()) == str(current_day)):
				t_weight = data['body']['measuregrps'][x]['measures'][0]['value']
				t_unit = data['body']['measuregrps'][x]['measures'][0]['unit']
				t_date = data['body']['measuregrps'][x]['date']
				buf.write("%.2f" % (t_weight/math.pow(10,-t_unit)))
				buf.write(" ")

		buf.write(str(current_day) + " ")
		buf.write(WeekDay[current_day.weekday()] + "<br>")

	# print scales data
	for x in range(0,len(data['body']['measuregrps'])-1):
	    t_weight = data['body']['measuregrps'][x]['measures'][0]['value']
	    t_unit = data['body']['measuregrps'][x]['measures'][0]['unit']
	    t_date = data['body']['measuregrps'][x]['date']
	    buf.write(str(datetime.datetime.fromtimestamp(t_date).date()) + "<br>")
	    buf.write(WeekDay[datetime.datetime.fromtimestamp(t_date).date().weekday()] + "<br>")
	    buf.write("%.2f" % (t_weight/math.pow(10,-t_unit)))
	    buf.write("kg<br><br>")

	# print strava
	for x in range(0,len(data_strava)-1):
	    buf.write(str(data_strava[x]['start_date_local'].split("T")[0]) +"<br>")
	    #buf.write(datetime.datetime.fromtimestamp(data_strava[x]['start_date_local']) +"<br>")
	    buf.write("Time: " + str(data_strava[x]['start_date_local'].split("T")[1]) + "<br>")
	    buf.write(str(data_strava[x]['name']) + "<br>")
	    buf.write(str(data_strava[x]['distance']) + "<br>")
	    temp_mins = data_strava[x]['elapsed_time']/60
	    buf.write( str(temp_mins) + ":" + str(data_strava[x]['elapsed_time']%60) + "<br>")
	    buf.write("<br>")

	 # print trackyoureating
	 # reverse the data so newest first

	for x in range(len(data_tye)-1,-1,-1):
		buf.write(str(datetime.datetime.strptime(data_tye[x]['date'], '%Y-%m-%d').date())+ "<br>")
		buf.write("Calories:" + str(data_tye[x]['calories']) + "<br>")
		buf.write("Protein:" + str(data_tye[x]['protein']) + "<br>")
		buf.write("Carbs:" + str(data_tye[x]['carbs']) + "<br>")
		buf.write("Fat:" + str(data_tye[x]['fats']) + "<br>")
		buf.write("<br>")


	# temp stuff to delete later
	buf.write(str(len(data_tye)) + "<br>")
	buf.write(str(len(data['body']['measuregrps'])) + "<br>")
	buf.write(str(len(data_strava)) + "<br>")



 
	#Actually return a template with all the correct data
	return buf2.getvalue()


class OneDayData(object):
    def __init__(self, date=datetime.datetime.today(), bodyweight = 0.0, calories = 0, protein =0, fat =0, carbs =0, strava_description = "", strava_distance=0,strava_time=0):
		self.date = date

		self.bodyweight = bodyweight

		self.calories = calories
		self.protein = protein
		self.fat = fat
		self.carbs = carbs

		self.strava_description = strava_description
		self.strava_distance = strava_distance
		self.strava_time = strava_time

	
	