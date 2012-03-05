#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
# (c) Janne Mäntyharju 2012

import time
import serial
import string
import urllib2
import socket
import os
import atexit
from pysqlite2 import dbapi2 as sqlite

CURRENT_DELAY = 10	# Measure current power consumption every 10 seconds
CUMULATIVE_DELAY = 5 * 60	# Measure power consumption during last 5 minutes
SERVER_DELAY = 0.3
TICK_DURATION = 0.000128 # One "current" unit is this many seconds
IMPULSE_KW = 480	# No. of impulses in kWh
DATABASE = "powermeter.db"	# Database file
SOCKET = "/tmp/powermeter"

class Measurer:    
    def __init__(self):
        self.port = None
        pass
        
    def start(self):
        if self.port != None and self.port.isOpen():
            self.port.close()
            
        port = None
        while port == None:
            for i in range(0,9):
                portname = "/dev/ttyUSB" + str(i)
                if os.path.exists(portname):
                    port = portname
                    break
            time.sleep(2)
        
        self.port = serial.Serial(port, 19200, timeout=1)
        self.port.flushInput()
        value = None
        while value == None:
            try:
                value = self.cumulative()
            except:
                return
        
    def close(self):
        self.port.close()

    def current(self):
        self.port.write("VALI\r")
        s=self.port.read(10)
        if string.find(s,'\r') == -1:
            return None
        else:
            s = string.strip(s,"\r")
            
        try:
            return (3600 / (float(s) * TICK_DURATION)) / IMPULSE_KW
        except:
            print "Got err"
        return None

    def cumulative(self):
        value = None
        
        while value == None:
            self.port.write("LUKU\r")
            s=self.port.read(10)
            if string.find(s,'\r') != -1:
                s = string.strip(s,"\r")
                try:
                    value = (float(s) / IMPULSE_KW) * (3600 / CUMULATIVE_DELAY)
                except:
                    print "Got err"
            time.sleep(0.5)
        
        return value
    
    def temperature(self):
        temp = None
        
        try:
            f = urllib2.urlopen("http://weather.jyu.fi")
        except:
            print "Error reading temperature"
            return None
        
        lines = f.readlines()
        f.close()
        
        for l in lines:
            if(string.find(l, "Temperature (outside):") != -1):
                temp = float(string.split(l)[2])
                break
            
        print "Temperature: ", temp
        return temp
    
    def __del__(self):
        self.port.close()

class Database:    
    def __init__(self):
        self.connection = sqlite.connect(DATABASE, check_same_thread = False)

    def write(self, m, temp):
        cursor = self.connection.cursor()
        cursor.execute("insert into measurements (t,kw,temp) values(?, ?, ?)", (time.time(),m, temp))
        self.connection.commit()
        cursor.close()
        
    def __del__(self):
        self.connection.close()
        
class Server:
    def __init__(self):
        if os.path.exists(SOCKET):
            os.remove(SOCKET)     
        print "Opening socket..."
        self.server = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(SOCKET)
        os.chmod(SOCKET, 666)
        self.server.settimeout(5)
        self.server.listen(1)
        
        self.temp = 0.0
        self.consumption = 0.0
        
    def set_temp(self,temp):
        self.temp = temp
        
    def set_consumption(self, consumption):
        self.consumption = consumption
    
    def handle(self):
        try:
            (conn, addr) = self.server.accept()
            del addr
        except:
            return
        
        print "connection started"
        datagram = None
        while datagram != "END":
            handled = False
            try:
                datagram = conn.recv( 1024 )
            except:
                break
        
            print "Message: " + datagram
            if datagram == "TEMP":
                handled = True
                try:
                    conn.send(str(self.temp))
                except:
                    break
                
            if datagram == "CONSUMPTION":
                handled = True
                try:
                    conn.send(str(self.consumption))
                except:
                    break
            if handled == False:
                break
                
        print "Closing connection"
        conn.close()
    
    def __del__(self):
        self.server.close()
        os.remove(SOCKET)

def at_exit(measurer, database, server):
    del measurer
    del database
    del server
    print "Exiting.."
    
def main():
    server_timer = time.time()
    current_timer = time.time()
    cumulative_timer = time.time()
    current_consumption = None
    measurer = Measurer()
    measurer.start()
    database = Database()
    server = Server()
    
    atexit.register(at_exit, measurer, database, server)        
    
    print "Started"
    while 1:
        if time.time() > current_timer + CURRENT_DELAY:
            print "measuring consumption"
            try:
                current_consumption = measurer.current()
            except:
                measurer.start()
                continue
            server.set_consumption(current_consumption)
            print "consumption", current_consumption
            current_timer = time.time()

        if time.time() > cumulative_timer + CUMULATIVE_DELAY:
            print "measuring cumulative"
            try:
                m = measurer.cumulative()
            except:
                measurer.start()
                continue
            if m is not None:
                temp = measurer.temperature()
                server.set_temp(temp)
                database.write(m, temp)
                print "ticks",m
                cumulative_timer = time.time()
        if time.time() > server_timer + SERVER_DELAY:
            server.handle()
            server_timer = time.time()
        
        time.sleep(1)

if __name__ == '__main__':
    main()
