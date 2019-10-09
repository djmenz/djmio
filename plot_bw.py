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
    plt.savefig('bw_years.png',bbox_inches='tight')

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