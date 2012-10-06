#!/opt/local/bin/python
# -*- coding: iso-8859-1 -*-
# (c) Janne Mäntyharju, 2012

"""
    CREATE TABLE measurements (t integer,kw float, temp float);
    create table cache (t integer,type integer, value float);
    insert into cache (t,type,value) values (0,1,0.0);
    insert into cache (t,type,value) values (0,2,0.0);
    insert into cache (t,type,value) values (0,3,0.0);
    insert into cache (t,type,value) values (0,4,0.0);
    insert into cache (t,type,value) values (0,5,0.0);
    insert into cache (t,type,value) values (0,6,0.0);
"""

import os
os.environ['HOME'] = "/Users/Shared" 
import matplotlib
matplotlib.use('Agg')
import pylab
import sqlite3
import time
import sys
import cgi
import cgitb
import stat
import urllib2
import string
from PIL import Image
import ImageDraw
import ImageFont
cgitb.enable()

GRAPH = "/tmp/graph.png"
DATABASE = "/Users/Shared/powermeter.db"	# Database file
UPDATE_TIME = 30 * 60 # Update graph every 30 mins
MEASUREMENT_TIMEOUT = 30 * 60 # Don't display data if over 30 mins old
TICK_DURATION = 0.001 # One "current" unit is this many seconds
IMPULSE_KW = 1000	# No. of impulses in kWh

def graph(database, start, stop, minutes):
    x_data=[]
    y1_data=[]
    y2_data=[]
    
    for i in range(start, stop, minutes * 60):
        data = database.get_average(i, i + minutes * 60)
        for j in range(i, i + minutes * 60, 60):
            y1_data.append(data[0])
            y2_data.append(data[1])
            x_data.append(pylab.datetime.datetime.fromtimestamp(j))
            
    fig = pylab.figure(figsize = (8, 4.7), dpi = 100)
    ax1 = fig.add_subplot(111)
    ax1.plot_date(x_data,y1_data,fmt='')
    a=pylab.datetime.datetime.fromtimestamp(start)
    fromstr="%i-%i-%i %i:%02i" % (a.day,a.month,a.year,a.hour,a.minute)
    a=pylab.datetime.datetime.fromtimestamp(stop)
    tostr="%i-%i-%i %i:%02i" % (a.day,a.month,a.year,a.hour,a.minute)
    pylab.title("From %s to %s, averaged every %i minutes" % (fromstr,tostr,minutes))
    ax1.set_ylabel("kW/h", color = 'b')
    for tl in ax1.get_yticklabels():
        tl.set_color('b')
    ax1.grid(True)
    fig.autofmt_xdate()
    
    ax2 = ax1.twinx()
    ax2.plot_date(x_data ,y2_data, fmt = 'r')
    ax2.set_ylabel(u"\u00b0c", color = 'r')
    for tl in ax2.get_yticklabels():
        tl.set_color('r')
        
    fig.savefig(GRAPH)

def weather():
    temp = None
    wind = None
    
    try:
        f = urllib2.urlopen("http://weather.jyu.fi")
    except:
        print "Error reading temperature"
        return (temp, wind)
    
    lines = f.readlines()
    f.close()
    
    for l in lines:
        if(string.find(l, "Temperature (outside):") != -1):
            temp = float(string.split(l)[2])
            break
    
    for l in lines:
        if(string.find(l, "Wind Speed (the highest within an hour):") != -1):
            wind = float(string.split(l)[7])
            break
    
    print "Temperature: ", temp
    print "Wind: ", wind
    return (temp, wind)

class Database:
    CONSUMPTION = 1
    WIND = 2
    TEMP = 3
    CUMULATIVE = 4
    INTEMP = 5
    HUMIDITY = 6
    
    def __init__(self):
        self.connection = sqlite3.connect(DATABASE)
   
    def get_average(self,start,stop):
        cursor = self.connection.cursor()
        cursor.execute("select avg(kw),avg(temp) from measurements where t > ? and t < ?", (start,stop))
        result = cursor.fetchone()
        kw = None
        temp = None
        if result[0] != None:
            kw = float(result[0])
        if result[1] != None:
            temp = float(result[1])
        cursor.close()
            
        return kw, temp
    
    def write(self, m, temp):
        cursor = self.connection.cursor()
        cursor.execute("insert into measurements (t,kw,temp) values(?, ?, ?)", (time.time(), m, temp))
        self.connection.commit()
        cursor.close()
        self.write_cache(self.TEMP, temp)

    def write_cache(self, type, value):
        cursor = self.connection.cursor()
        cursor.execute("update cache set t=?,value=? where type=?", (time.time(), value, type))
        self.connection.commit()
        cursor.close()
    
    def get_cache(self, value):
        cursor = self.connection.cursor()
        cursor.execute("select t,value from cache where type=?", (value,))
        result = cursor.fetchone()
        cursor.close()
        if result[0] < (time.time() - MEASUREMENT_TIMEOUT):
            return [0, 0.0]
        return result

    def set_consumption(self, consumption):
        self.write_cache(self.CONSUMPTION, consumption)
    
    def get_consumption(self):
        return self.get_cache(self.CONSUMPTION)[1]

    def get_cumulative(self):
        return self.get_cache(self.CUMULATIVE)[0]

    def set_cumulative(self):
        self.write_cache(self.CUMULATIVE, 0.0)

    def set_temp(self, temp):
        self.write_cache(self.TEMP, temp)

    def get_temp(self):
        return self.get_cache(self.TEMP)[1]

    def set_wind(self, wind):
        self.write_cache(self.WIND, wind)

    def get_wind(self):
        return self.get_cache(self.WIND)[1]

    def get_inTemp(self):
        return self.get_cache(self.INTEMP)[1]

    def set_inTemp(self, inTemp):
        self.write_cache(self.INTEMP, inTemp)

    def get_humidity(self):
        return self.get_cache(self.HUMIDITY)[1]
 
    def set_humidity(self, humidity):
        self.write_cache(self.HUMIDITY, humidity)        
    
def main():    
    time_from = 60*60*24*7
    time_to = int(time.time())
    time_interval = 120
    current = None
    cumulative = None
    inTemp = None
    humidity = None

    db = Database()
    
    parms = cgi.FieldStorage()
    
    try:
        humidity = float(parms.getfirst("humidity"))
        db.set_humidity(humidity)
	print "Content-Type: text/html"
        print
        print "Humidity", humidity
        return
    except:
        pass

    try:
        inTemp = float(parms.getfirst("inTemp"))
        db.set_inTemp(inTemp)
        print "Content-Type: text/html"
        print
        print "Temp (inside)", inTemp
        return
    except:
        pass

    try:
        current = float(parms.getfirst("current"))
    except:
        pass
            
    if current != None:
        if current == 0:
            consumption = 0
        else:
            consumption = (3600 / (current * TICK_DURATION)) / IMPULSE_KW
        db.set_consumption(consumption)
        print "Content-Type: text/html"
        print
        print "Consumption", consumption
        return
    
    try:
        cumulative = float(parms.getfirst("cumulative"))
    except:
        pass

    if cumulative != None:
        cumulative_delay = db.get_cumulative()
        db.set_cumulative()
        print "Content-Type: text/html"
        print
        if (time.time() - cumulative_delay) < (60 * 20):
            cumulative_calc = (cumulative / IMPULSE_KW) * (3600 / (time.time() - cumulative_delay))
            temp, wind = weather()
            db.write(cumulative_calc, temp)
            db.set_wind(wind)
            print "Cumulative", cumulative_calc, "Ticks", cumulative
        else:
            print "cumulative delay set"
        return
        
    recent = False
    try:
        stats = os.stat(GRAPH)
        if stats[stat.ST_MTIME] > time.time() - UPDATE_TIME:
            recent = True
    except:
        pass

    try:
        time_from = int(parms.getfirst("from"))
	recent = False
    except:
        pass
    
    try:
        time_to = int(parms.getfirst("to"))
	recent = False
    except:
        pass
        
    try:
        time_interval = int(parms.getfirst("interval"))
	recent = False
    except:
        pass

    if recent == False:
        graph(db, int(time.time() - time_from), time_to, time_interval)

    image = Image.open(GRAPH)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/Library/Fonts/Arial Black.ttf', 14)
    draw.text((20, 450), "Temp(Inside): %.2f c Humidity: %.2f %%  Consumption: %.2f kW/h Temp(Out): %.1f c  Wind: %.1f m/s" % (db.get_inTemp(), db.get_humidity(), db.get_consumption(), db.get_temp(), db.get_wind()), font=font, fill="black")

    print "Content-Type: image/png"
    print
    image.save(sys.stdout, "PNG")

if __name__ == '__main__':
    main()

