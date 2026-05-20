# ARLO-FHEM

## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Config](#config)
- [Usage](#usage)

## Introduction

"arlo-fhem" is a module for sending control commands from FHEM to ARLO and also receving status information from ARLO and saving them to FHEM.

It is written in Python and based on the Arlo Python library "pyarlo" (https://github.com/twrecked/pyaarlo).

"pyarlo" is able to handle the Arlo two factor authentication by default, so you do not need to handle that.

I am using this daemon to automatically activate and deactivate my Arlo cams from FHEM. E.g. if I open the door to the garden, FHEM automatically disables the cameras there so that I do not get alarms and recordings as long as I am outside.

So it is currently only supporting these basic commands but not something like motion detection etc.

## Prerequisites

- FHEM (https://fhem.de/) with TELNET access enabled

 >**Remark:** The script expects a password prompt from TELNET so you should not use "localhost" as your FHEM server (as no password is needed in this case) but use the public IP/DNS name instead. If TELNET is only available via "localhost" then you need to adapt the Python module.

- Python 3.8 installed on the FHEM server
- Debian command "unbuffer" ("apt install expect")
- Debian command "nc" ("apt install netcat")
- Several Python modules
    - requests ("apt install python-requests")
    - monotonic ("apt install python3-monotonic")
    - configparser ("apt install python-configparser")
    - sseclient 
    - unidecode ("apt install python3-unidecode")
    - cloudscraper ("pip install cloudscraper")


## Installation

On the FHEM server run the following commands as the user who is running FHEM:

```
cd /opt/fhem
git clone https://github.com/m0urs/arlo-fhem.git
cd arlo-fhem
```

To create the Debian service for the arlo-fhem daemon, run the following command as "root" on the FHEM server:

```
ln -s /opt/fhem/arlo-fhem/arlo-fhem.service /etc/systemd/system 
systemctl daemon-reloads
systemctl enable arlo-fhem
systemctl start arlo-fhem
```
The daemon sends all log messages to the Debian syslog ("/var/log/syslog")

## Config

The script is looking for a config file where you define several parameters. See "arlo-fhem.cfg.sample" as a sample of how the file looks like.

The config file is named "arlo-fhem.cfg" and needs to be put in the same directory as "arlo-fhem.py". You can also specifiy a different name and path for that file by adding the "--configfile|-c" switch.

```
[CREDENTIALS]

# Arlo account user name
USERNAME = _arlo_username_

# Arlo account password
PASSWORD = _arlo_password_

[2FA]

# Host name of IMAP sever for 2FA authentication token
IMAPSERVER = _imap_hostname_

# IMAP user name
IMAPUSER = _imap_user_

# IMAP user password
IMAPPASSWORD = _imap_password_

[SOCKET]

# IP address of communication socket with FHEM (mostly "127.0.0.1")
TCP_IP = 127.0.0.1

# Socket port number of communication socket
TCP_PORT = 5005

# Buffer size for communication socket (normally no need to change)
BUFFER_SIZE = 1024

[LOCATION]

# Name of the location which should be used (as defined in Arlo app)
LOCATION_NAME = _location_name_

[MISC]

# Maximum of login attempts
MAX_TRIES = 5

# Time in seconds between every login attempt
LOGIN_WAIT = 60

[FHEM]

# FHEM host name
FHEM_HOST = _fhem_host_

# FHEM telnet port
FHEM_PORT = 7072

# FHEM telnet password
FHEM_PASSWORD = _fhem_password_

```

## Usage

The daemon is running as a Debian service in the background. 

It first tries to logon to the Arlo account. If the account is protected with 2FA, it automatically gets the 2FA token from the IMAP account provided in the config file.

If the login attempt was not successful, it tries to relogin several times. You can provide the number of times and the waiting time between retries in the config file.

If the login was not successfull it ends the service.

After it was successfully able to login to the Arlo account, the daemon is waiting for commands.

The commands are sent as text messages to a TCPIP socket. To send messages you can use the "nc" (netcat) command.

**Example:**

Linux ("netcat" package):

```
echo 'command' |  nc -N 127.0.0.1 5005
```

Windows (ncat.exe from https://nmap.org/ncat/):

```
echo command | c:\tools\ncat.exe --send-only 127.0.0.1 5005
```

where "5005" is the port number you had defined as socket port number in the config file.

We provided a command file for sending commands. "cl.bat" for Windows, and "cl.sh" for Linux. Just use the syntax

```
cl.bat <your command>
```
resp.
```
./cl.sh <your command>
```



The following commands are currently implemented:

|Command            |Example    |Purpose
|---	            |---	    |---
|quit               |quit       |quit the daemon (you can also end via service like "systemctl stop arlo-fhem" )
|set-mode \<mode>	|set-mode aktiviert	|Set a specified mode (see next table for all supported modes)
|get-mode           |get-mode   |Reads all modes and writes the modes as readings to a device in FHEM
|list-devices       |list-devices |Lists all device sknown to the system with type and id to syslog.
|list-locations     |list-locations   |Writes a list of all locations known to the system with detailed information to syslog

<br>

Mode | Purpose
--- | ---
aktiviert | Set the "armeAway" state of the location
deaktiviert | Set the "standy" state for the location
aktiviert_tag | same as "aktiviert"; only for backward compatibility
garten | Set the "armHome" state of the location
garten_hinten | same as "garten"; only for backward compatibility
