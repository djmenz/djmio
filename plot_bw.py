import requests
import datetime
import pandas as pd
import collections

import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import djmv2
import djm_utils
import math
import boto3


def epoch_to_local_time_yy(epoch_time):
    date = datetime.datetime.fromtimestamp(epoch_time).strftime('%Y-%m-%d')
    return date

def main():
    output_file_name = 'bw_years.png'
    
    djmv2.refresh_withings_token()
    auth_urls = djmv2.get_user_data()

    try:
        data_withings = djmv2.get_data_withings(auth_urls['withings']['url'], {"Authorization": "Bearer {}".format(auth_urls['withings']['auth_token_dm'])})
    except:
        data_withings = []

    clean_data = []

    for data_entry in data_withings[::-1]:
        this_day = djm_utils.epoch_to_ordinal(data_entry['date'])
        try:
            t_weight = data_entry['measures'][0]['value']
            t_unit = data_entry['measures'][0]['unit']
            t_date = data_entry['date']
            t_date_human = epoch_to_local_time_yy(t_date)
            tempweight = ("%.2f" % (t_weight/math.pow(10,-t_unit)))    
            clean_data.append([t_date_human,float(tempweight)])
       
        except:
            print('key error withings')
            continue   

    #Adding manual old entries
    #import pdb; pdb.set_trace() 
    manual_data = [
        ['2012-04-29', 80.5],
        ['2012-06-24', 82.2],
        ['2012-11-09', 89.2],
        ['2013-03-10', 83.9],
        ['2013-06-14', 81.0],
        ['2014-03-09', 81.6],
        ['2014-06-05', 80.9],
        ['2014-12-03', 78.42],
        ['2015-02-01', 73.9],
        ['2015-05-19', 78.4],
        ['2015-10-17', 78.0],
        ['2016-10-23', 73.8]                                                
    ]

    #clean_data = manual_data + clean_data

    date_list,bw_list = zip(*clean_data)



    dates = [pd.to_datetime(d) for d in date_list]


    x_var = dates
    y_var = bw_list

    

    fig, ax = plt.subplots(1,1)
    
    years = mdates.YearLocator()
    months = mdates.MonthLocator()

    monthsFmt = mdates.DateFormatter('%b') 
    yearsFmt = mdates.DateFormatter('\n\n%Y')

    ax.xaxis.set_minor_locator(months)
    ax.xaxis.set_major_locator(years)

    ax.xaxis.set_minor_formatter(monthsFmt)
    ax.xaxis.set_major_formatter(yearsFmt)
   
    ax.grid(axis='y')
    ax.grid(axis='x', which='both')
    ax.plot_date(x = x_var, y = y_var)
    plt.setp(ax.xaxis.get_minorticklabels(), rotation=90)
    #plt.show()

    fig = matplotlib.pyplot.gcf()
    fig.set_size_inches(18.5, 10.5)
    plt.savefig(output_file_name,bbox_inches='tight')

    s3 = boto3.resource('s3')
    file_loc = 'bw_years.png'
    data = open(file_loc, 'rb')
    
    try:
        response = s3.Bucket('djmio').put_object(Key='bw_years.png', Body=data)
    except:
        print("error uploading")
        return False

if __name__ == '__main__':
    main()