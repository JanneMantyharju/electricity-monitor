#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
# (c) Janne Mäntyharju, 2012

import os
os.environ['HOME'] = "/home/www-data" 
import matplotlib
matplotlib.use('Agg')
import pylab
from pysqlite2 import dbapi2 as sqlite
import socket
import time
import sys
import cgi
import cgitb
cgitb.enable()

SOCKET = "/tmp/powermeter"
DATABASE = "/home/www-data/powermeter.db"	# Database file

def graph(database, start, stop, minutes, current_temp, current_consumption):
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
    fromstr="%i-%i-%i %i:%i" % (a.day,a.month,a.year,a.hour,a.minute)
    a=pylab.datetime.datetime.fromtimestamp(stop)
    tostr="%i-%i-%i %i:%i" % (a.day,a.month,a.year,a.hour,a.minute)
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
        
    fig.text(.6, 0, "Consumption: %f\nTemperature: %f" % (current_consumption, current_temp))
    
    print "Content-Type: image/png"
    print
    fig.savefig(sys.stdout,format="png")

class Database:    
    def __init__(self):
        self.connection = sqlite.connect(DATABASE)
   
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
    
def main():    
    time_from = 60*60*24*7
    time_to = int(time.time())
    time_interval = 60
    
    parms = cgi.FieldStorage()
    
    try:
        time_from = int(parms.getfirst("from"))
    except:
        pass
    
    try:
        time_to = int(parms.getfirst("to"))
    except:
        pass
        
    try:
        time_interval = int(parms.getfirst("interval"))
    except:
        pass
    
    current_temp = 0.0
    current_consumption = 0.0
    
    if os.path.exists(SOCKET):
        client = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )
        client.settimeout(2)
        client.connect(SOCKET)
        try:
            client.send("TEMP")
            datagram = client.recv(1024)
            current_temp = float(datagram)
            client.send("CONSUMPTION")
            datagram = client.recv(1024)
            current_consumption = float(datagram)
            client.send("END")
        except Exception as inst:
            print inst
        
    graph(Database(), int(time.time() - time_from), time_to, time_interval, current_temp, current_consumption)    

if __name__ == '__main__':
    main()

