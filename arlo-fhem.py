#!/usr/bin/env python3

# arlo-fhem.py / Arlo Daemon for FHEM
# https://github.com/m0urs/arlo-fhem
# Based on https://github.com/twrecked/pyaarlo
# Michael Urspringer

VERSION = "1.1.15"

import pyaarlo
import argparse
import configparser
import datetime
import errno
import logging
import os
import pprint
import socket
import sys
import telnetlib
import time
import unidecode

# Login to Arlo Account, retry if not successfull
def loginToArlo(username, password, tfa_host, tfa_username, tfa_password, max_tries, login_wait):
    count = 0
    arlo = ""
    while count < max_tries:
        count = count + 1 
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - Trying to connect ",count," of ",max_tries)
        arlo = pyaarlo.PyArlo(username=username, password=password,tfa_source='imap', tfa_type='email', tfa_host=tfa_host, tfa_username=tfa_username, tfa_password=tfa_password, synchronous_mode=False, refresh_devices_every=1,reconnect_every=90, stream_timeout=180, request_timeout=120, user_agent='!Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58', backend='sse', mqtt_hostname_check=False, verbose_debug=True)
        if arlo.is_connected:
            break
        if count == max_tries:
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - UNABLE TO CONNECT - aborting")
            sys.exit(-1)
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - UNABLE TO CONNECT - retrying after ",login_wait," seconds")
        time.sleep(login_wait)
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - CONNECTED")
    return arlo

# Send a command to FHEM via TELNET
def sendCommandtoFHEM(fhem_host, fhem_port, fhem_password, fhem_command):
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - Send FHEM command: ",fhem_command)
    tn = telnetlib.Telnet(fhem_host,fhem_port)
    tn.read_until(b"Password: ")
    tn.write(fhem_password.encode("ascii") + b"\n")
    tn.write(fhem_command.encode("ascii") + b"\n")
    tn.write(b"quit\n")
    tn.close()

def getDeviceFromName(name, devices):
    for device in devices:
        if device.name == name:
            return(device)
    return("")

def getLocationFromName(name, locations):
    for location in locations:
        if location.name == "location_"+name:
            return(location)
    return("")

print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - version", VERSION)

# set up logging, change ERROR or INFO to DEBUG for a *lot* more information
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='debug.log')
_LOGGER = logging.getLogger('arlo-fhem')

# Check command line parameters
parser = argparse.ArgumentParser()
parser.add_argument('--configfile', '-c', default='./arlo-fhem.cfg', help='Path to config file, use ./arlo-fhem.cfg if empty')
args = parser.parse_args()

configfile=args.configfile

# Initialize config file
if not os.path.isfile(configfile):
    print("Error: Config file "+configfile+" not found")
    sys.exit(errno.ENOENT)

config = configparser.ConfigParser()
config.read(configfile)

# Credentials for Arlo
USERNAME = config.get("CREDENTIALS", "USERNAME")
PASSWORD = config.get("CREDENTIALS", "PASSWORD")

# Credentials for 2FA via IMAP
IMAPSERVER = config.get("2FA", "IMAPSERVER")
IMAPUSER = config.get("2FA", "IMAPUSER")
IMAPPASSWORD = config.get("2FA", "IMAPPASSWORD")

# Definitions for Communication Socket
TCP_IP = config.get("SOCKET", "TCP_IP")
TCP_PORT = int(config.get("SOCKET", "TCP_PORT"))
BUFFER_SIZE = int(config.get("SOCKET", "BUFFER_SIZE"))

# Location Name
LOCATION_NAME = config.get("LOCATION","LOCATION_NAME")

# Misc parameters
MAX_TRIES = int(config.get("MISC", "MAX_TRIES"))
LOGIN_WAIT = int(config.get("MISC", "LOGIN_WAIT"))

# FHEM parameters
FHEM_HOST = config.get("FHEM", "FHEM_HOST")
FHEM_PORT = int(config.get("FHEM", "FHEM_PORT"))
FHEM_PASSWORD = config.get("FHEM", "FHEM_PASSWORD")

# Login to Arlo, use 2FA via IMAP Mail if required
arlo = loginToArlo(USERNAME,PASSWORD,IMAPSERVER,IMAPUSER,IMAPPASSWORD,MAX_TRIES,LOGIN_WAIT)

# pprint.pprint(vars(arlo))

# Get correct location element according to the Name
location = getLocationFromName(LOCATION_NAME, arlo.locations)
print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - Use location: ",location.name)

while True:

    # Open a TCPIP socket for communication with FHEM
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)
    conn, addr = s.accept()
    
    while True:

        received_command = conn.recv(BUFFER_SIZE)
        if not received_command: break

        received_command = received_command.decode('utf8').replace("\n", "")
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - Received command: ",received_command)

        received_command = received_command.split(" ")
        try:
            command = received_command[0]
        except IndexError:
            command = ""
        try:
            parameter1 = received_command[1]
        except IndexError:
            parameter1 = ""
        try:
            parameter2 = received_command[2]
        except IndexError:
            parameter2 = ""

        if command == 'list-devices':
            for device in arlo._devices:
                print("device: name={} | deviceType={} | device_id={}".format(device["deviceName"], device["deviceType"], device["uniqueId"]))

        elif command == 'list-locations':
            # List all locations
            for location in arlo.locations:
                print("********** location: name={}, uid={} **********".format(location.name,location._uid))
                pprint.pprint(location._attrs)
                print("********************".format(location.name,location._uid))

        elif command == 'set-mode':
            if parameter1 == 'deaktiviert':
                location.mode = "standby"
            elif parameter1 == 'aktiviert':
                location.mode = "armAway"
            elif parameter1 == 'aktiviert_tag':
                location.mode = "armAway"
            elif parameter1 == 'garten':
                location.mode = "armHome"
            elif parameter1 == 'garten_hinten':
                location.mode = "armHome"
            else:
                print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - set-mode - unknown mode parameter - ignoring")
                break

        elif command == 'get-mode':
            statusHome = location.mode
            sendCommandtoFHEM(FHEM_HOST, FHEM_PORT, FHEM_PASSWORD, "setreading Arlo_Cam.dum status-Home "+statusHome)
            statusBridgeAZMichael = location.mode
            sendCommandtoFHEM(FHEM_HOST, FHEM_PORT, FHEM_PASSWORD, "setreading Arlo_Cam.dum status-Bridge_AZMichael "+statusBridgeAZMichael)
            statusBridgeAZSabine = location.mode
            sendCommandtoFHEM(FHEM_HOST, FHEM_PORT, FHEM_PASSWORD, "setreading Arlo_Cam.dum status-Bridge_AZSabine "+statusBridgeAZSabine)
            if statusHome == 'standby':
                currentMode = "Deaktiviert"
            elif statusHome == 'armAway':
                currentMode = "Aktiviert"
            elif statusHome == 'armHome':
                currentMode = "Garten_hinten"
            else:
                currentMode = "Undefiniert"
            sendCommandtoFHEM(FHEM_HOST, FHEM_PORT, FHEM_PASSWORD, "setreading Arlo_Cam.dum currentMode "+currentMode)

        elif command == 'quit':
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - quit command received ... exiting!")
            arlo.stop()
            conn.close()
            sys.exit(0)

        else:
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "- arlo-fhem - Unknown command "+command+" - ignoring")

    conn.close()
