#!/usr/bin/python
import paho.mqtt.client as mqtt
import serial
import os
import json
import time
import sys
import threading
import socket
import paho.mqtt.publish as publish
from itertools import product
CLOUD="mqtt.letsandy.com"
LOCAL="127.0.0.1"

DEBUG="F"
if len(sys.argv) == 2:
   if sys.argv[1] == "-d":
      DEBUG="T"

ser = serial.Serial("/dev/ttyAMA0", 19200)
ser.flushInput()
ser.flushOutput()
CFG_FILE="/home/pi/andy/cfg/masterJSON.cfg"
STATUS_FILE="/home/pi/andy/cfg/statusJSON.cfg"
STATUS_JSON=""
MASTER_JSON=""
PARSED_JSON=""
PARSED_STATUS_JSON=""
ID=""

def logit(message):
    if DEBUG == "T":
       print message

def readMasterFile():
    global MASTER_JSON
    global PARSED_JSON
    target = open(CFG_FILE, 'r')
    MASTER_JSON=target.read()
    PARSED_JSON=json.loads(MASTER_JSON) 

def readStatusFile():
    global STATUS_JSON
    global PARSED_STATUS_JSON
    status_file=open(STATUS_FILE,'r')
    STATUS_JSON=status_file.read()
    PARSED_STATUS_JSON=json.loads(STATUS_JSON)
    status_file.close()

def writeStatusFile():
    LINE=json.dumps(PARSED_STATUS_JSON)  
    status_file=open(STATUS_FILE,'w')
    status_file.write(LINE)
    status_file.close()

def getID():
   global ID
   CONFIG_FILE="/home/pi/andy/cfg/config.cfg"
   file = open(CONFIG_FILE, 'r')
   CONFIG_JSON=file.read()
   PARSED_CONFIG_JSON=json.loads(CONFIG_JSON)
   ID=PARSED_CONFIG_JSON['ID']
    
def publishMQTT(topic,message):
    publishMQTTCLOUD(topic,message)
    publishMQTTLOCAL(topic,message)

def clientConnectCLOUD():
    global clientCLOUD
    clientCLOUD = mqtt.Client()
    clientCLOUD.username_pw_set("andy","andy!@#$%")
    try:
       clientCLOUD.connect(CLOUD, 1883, 60)
    except socket.error as err:
       logit("socket.err")
    clientCLOUD.loop_forever()

def clientConnectLOCAL():
    global clientLOCAL
    clientLOCAL = mqtt.Client()
    clientLOCAL.username_pw_set("andy","andy!@#$%")
    try:
       clientLOCAL.connect(LOCAL, 1883, 60)
    except socket.error as err:
       logit("socket.err")
    clientLOCAL.loop_forever()

t1=threading.Thread(target=clientConnectCLOUD)
t1.daemon = True
t1.start()

t2=threading.Thread(target=clientConnectLOCAL)
t2.daemon = True
t2.start()


def publishMQTTCLOUD(topic,message):
    global clientCLOUD
    try:
       clientCLOUD.publish(topic,message)
    except socket.error as err:
       logit("socket.err")

def publishMQTTLOCAL(topic,message):
    global clientLOCAL
    try:
       clientLOCAL.publish(topic,message)
    except socket.error as err:
       logit("socket.err")

#start_time = time.time()
#print("--- %s seconds ---" % (time.time() - start_time))

def processRawData(UNIQUE_ID,SWITCH_TYPE,BUTTON_NUMBER,SWITCH_STATUS,SWITCH_SPEED):
    FLAG=1
    for ROOM_NUMBER in range(len(PARSED_JSON['Room'])):
        for SWITCH_NUMBER in range(len(PARSED_JSON['Room'][ROOM_NUMBER]['Switch'])):
             CUR_UNIQUE_ID=PARSED_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['UNIQUE_ID']
             CUR_TYPE=PARSED_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['Type']
             CUR_SWITCH_NUMBER=PARSED_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['BUTTON_NUMBER']
             if (CUR_TYPE==SWITCH_TYPE and CUR_SWITCH_NUMBER==BUTTON_NUMBER and CUR_UNIQUE_ID==UNIQUE_ID):
                FLAG=0
                break
        if FLAG == 0:
           break
    

    start_time = time.time()
    if FLAG==0:
       PARSED_STATUS_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['SwitchStatus']=SWITCH_STATUS
       if (SWITCH_TYPE == "Dimmer" or SWITCH_TYPE == "Fan"):
          PARSED_STATUS_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['DimmerStatus']=SWITCH_SPEED
       writeStatusFile()

       CUR_ROOM=str(ROOM_NUMBER).rjust(2,'0')
       CUR_SWITCH=str(SWITCH_NUMBER).rjust(2,'0')
       CUR_DIMMER=str(SWITCH_SPEED).rjust(2,'0')
       STATUS="R"+CUR_ROOM+"S"+CUR_SWITCH+"D"+CUR_DIMMER+SWITCH_STATUS
       logit("Published "+STATUS)
       start_time = time.time()
       publishMQTT(ID+"/response/switchControl",STATUS)

#Main Function

logit("Program Started")

readMasterFile()
readStatusFile()
getID()
while True:
    RECORD=int(ser.read(1).encode("HEX"),16)
    if RECORD==254:
       BUFFER=[]
    BUFFER.append(RECORD)
   
    if RECORD==253: 
       logit("Raw Buffer " + ' '.join(str(x) for x in BUFFER))

       if BUFFER[4]==250:
          SWITCH_TYPE="Normal"
       elif BUFFER[4]==248:
          SWITCH_TYPE="Dimmer"
       elif BUFFER[4]==249:
          SWITCH_TYPE="Fan"
       elif BUFFER[4]==244:
          SWITCH_TYPE="Curtain"
       elif BUFFER[4]==245:
          SWITCH_TYPE="Scene"
       elif BUFFER[4]==45:
          SWITCH_TYPE="Learn"
          NETWORK_ID_1=str(BUFFER[1]).zfill(3)
          NETWORK_ID_2=str(BUFFER[2]).zfill(3)
          NETWORK_ID_3=str(BUFFER[3]).zfill(3)
          UNIQUE_ID=NETWORK_ID_1 + NETWORK_ID_2 + NETWORK_ID_3 

          ROOM_NUMBER=BUFFER[2]
          LEARN_CFG="/home/pi/andy/cfg/masterJSON.cfg"
          target = open(LEARN_CFG, 'r')
          MASTER_JSON=target.read()
          target.close()

          JSON_ROOM_NUM=-1
          for TEMP_ROOM_NUMBER in range(len(PARSED_JSON['Room'])):
              CUR_ROOM_NAME=PARSED_JSON['Room'][TEMP_ROOM_NUMBER]['RoomName'] 
              if CUR_ROOM_NAME=="Room"+str(ROOM_NUMBER):
                 JSON_ROOM_NUM=TEMP_ROOM_NUMBER
                 break

          NORMAL=0
          DIMMER=0
          FAN=0
          CURTAIN=0
          BELL=0

          if JSON_ROOM_NUM==-1:
             PARSED_JSON['Room'].append({"RoomName":"Room"+str(ROOM_NUMBER),"RoomIcon":"icon_20",'Switch':[]})
             JSON_ROOM_NUM=len(PARSED_JSON['Room'])-1
          else: 
             for TEMP_SWITCH_NUMBER in range(len(PARSED_JSON['Room'][JSON_ROOM_NUM]['Switch'])):
                CUR_TYPE=PARSED_JSON['Room'][JSON_ROOM_NUM]['Switch'][TEMP_SWITCH_NUMBER]['Type']
                if CUR_TYPE=="Normal": 
                   NORMAL=NORMAL+1
                elif CUR_TYPE=="Dimmer": 
                   DIMMER=DIMMER+1
                elif CUR_TYPE=="Fan": 
                   FAN=FAN+1
                elif CUR_TYPE=="Bell": 
                   BELL=BELL+1
                elif CUR_TYPE=="Curtain": 
                   CURTAIN=CURTAIN+1

          CUR_NORMAL=0
          CUR_DIMMER=0
          CUR_FAN=0
          CUR_BELL=0
          CUR_CURTAIN=0

          for i in range(5,(len(BUFFER)-1)):
             if BUFFER[i]==250:
                TYPE="Normal"
                NORMAL=NORMAL+1
                CUR_NORMAL=CUR_NORMAL+1
                COUNT=NORMAL
                CUR_COUNT=CUR_NORMAL
             elif BUFFER[i]==248:
                TYPE="Dimmer"
                DIMMER=DIMMER+1
                CUR_DIMMER=CUR_DIMMER+1
                COUNT=DIMMER
                CUR_COUNT=CUR_DIMMER
             elif BUFFER[i]==249:
                TYPE="Fan"
                FAN=FAN+1
                CUR_FAN=CUR_FAN+1
                COUNT=FAN
                CUR_COUNT=CUR_FAN
             elif BUFFER[i]==230:
                TYPE="Bell"
                BELL=BELL+1
                COUNT=BELL
                CUR_NORMAL=CUR_NORMAL+1
                CUR_COUNT=CUR_NORMAL
             elif BUFFER[i]==244:
                TYPE="Curtain"
                CURTAIN=CURTAIN+1
                CUR_CURTAIN=CUR_CURTAIN+1
                COUNT=CURTAIN
                CUR_COUNT=CUR_CURTAIN
             elif BUFFER[i]==0:
                continue
             PARSED_JSON['Room'][JSON_ROOM_NUM]['Switch'].append({"SwitchName":TYPE+str(COUNT),"SwitchIcon": "icon_20", "Type":TYPE,"UNIQUE_ID":UNIQUE_ID,"BUTTON_NUMBER":CUR_COUNT})
           
          json_data = json.dumps(PARSED_JSON)
          target = open(LEARN_CFG, 'w')
          target.write(json_data)
          target.close()

          readMasterFile()
          os.system("python /home/pi/andy/master/createStatus.py")
          readStatusFile()

          continue
       else:
          continue

       NETWORK_ID_1=str(BUFFER[1]).zfill(3)
       NETWORK_ID_2=str(BUFFER[2]).zfill(3)
       NETWORK_ID_3=str(BUFFER[3]).zfill(3)
       UNIQUE_ID=NETWORK_ID_1 + NETWORK_ID_2 + NETWORK_ID_3 


       SWITCH_NUMBER=str(BUFFER[5]) 
       
       if SWITCH_TYPE=="Curtain":
          if BUFFER[6]==01:
             SWITCH_STATUS="ON"
             SWITCH_SPEED=str(1)
          elif BUFFER[6]==02:
             SWITCH_STATUS="OF"
             SWITCH_SPEED=str(0)
          elif BUFFER[6]==00:
             SWITCH_STATUS="ST"
             SWITCH_SPEED=str(0)
          else:
            #To be done
             continue
       elif SWITCH_TYPE=="Scene":
          logit("Parsed Buffer " + UNIQUE_ID + " " + SWITCH_TYPE + " " + SWITCH_NUMBER + " " + SWITCH_STATUS + " " + SWITCH_SPEED)
          continue
         
       else:
          if BUFFER[6]==01:
             SWITCH_STATUS="ON"
             SWITCH_SPEED=str(1)
          elif BUFFER[6]==00:
             SWITCH_STATUS="OF"
             SWITCH_SPEED=str(0)
          else:
             SWITCH_STATUS="ON"
             SWITCH_SPEED=str((BUFFER[6]+9)/10) 
         
       logit("Parsed Buffer " + UNIQUE_ID + " " + SWITCH_TYPE + " " + SWITCH_NUMBER + " " + SWITCH_STATUS + " " + SWITCH_SPEED)

       if SWITCH_TYPE=="Bell" and SWITCH_STATUS=="ON":
          publishMQTT("response/bell","")
       else:
          processRawData(UNIQUE_ID,SWITCH_TYPE,SWITCH_NUMBER,SWITCH_STATUS,SWITCH_SPEED)

