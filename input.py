#!/usr/bin/python
import paho.mqtt.client as mqtt
import json
import os
import sys
import serial
import struct
import time
import socket
import subprocess
import paho.mqtt.publish as publish
DEBUG="F"
CLOUD="mqtt.letsandy.com"
LOCAL="127.0.0.1"
SERVER=LOCAL
if len(sys.argv) == 3:
   if sys.argv[2] == "-d":
      DEBUG="T"

if sys.argv[1] == "-c":
   SERVER=CLOUD 
else:
   SERVER=LOCAL

CFG_FILE="/home/pi/andy/cfg/masterJSON.cfg"
STATUS_FILE="/home/pi/andy/cfg/statusJSON.cfg"
STATUS_JSON=""
file = open(CFG_FILE, 'r')
MASTER_JSON=file.read() 
PARSED_JSON=json.loads(MASTER_JSON)

def logit(message):
    if DEBUG == "T":
       print message

def on_connect(client, userdata, flags, rc):
    logit("Connected with result code "+str(rc))
    ID=getID()
    client.subscribe(ID+"/request/switchControl",2)
    client.subscribe(ID+"/request/sceneControl",2)
    client.subscribe(ID+"/request/configure",2)
    client.subscribe(ID+"/request/completeStatus",2)
    client.subscribe(ID+"/request/adminControl",2)
    client.subscribe(ID+"/request/switchAllOff",2)
    client.subscribe(ID+"/request/command",2)
    client.subscribe(ID+"/request/ping",2)

def on_message(client, userdata, msg):
    TOPIC=msg.topic
    RAW_MESSAGE=msg.payload
    ID=getID()
    logit("RAW MQTT MESSAGE "+RAW_MESSAGE)
    if (TOPIC == ID+"/request/switchControl"):
        PARSED_JSON=json.loads(RAW_MESSAGE)
        REQUEST=PARSED_JSON['Request']
        commandProcess(REQUEST)
    elif (TOPIC ==ID+"/request/configure"):
        os.system("python /home/pi/andy/master/masterConfigure.py")
    elif (TOPIC ==ID+"/request/sceneControl"):
        sceneProcess(RAW_MESSAGE)
    elif (TOPIC ==ID+"/request/ping"):
         publishPingMQTT()
    elif (TOPIC ==ID+"/request/adminControl"):
        learnBoards(RAW_MESSAGE)
    elif (TOPIC ==ID+"/request/completeStatus"):
        publishCompleteStatus()
    elif (TOPIC ==ID+"/request/switchAllOff"):
        switchAllOff(RAW_MESSAGE)
    elif (TOPIC ==ID+"/request/command"):
        command(RAW_MESSAGE)

def getID():
   CONFIG_FILE="/home/pi/andy/cfg/config.cfg"
   file = open(CONFIG_FILE, 'r')
   CONFIG_JSON=file.read()
   PARSED_CONFIG_JSON=json.loads(CONFIG_JSON)
   ID=PARSED_CONFIG_JSON['ID']
   return ID

def command(RAW_MESSAGE):
    ID=getID()
    try:
       output = subprocess.check_output(RAW_MESSAGE+";exit 0",stderr=subprocess.STDOUT, shell=True)
       publishMQTT(ID+"/response/command",output)
    except subprocess.CalledProcessError as grepexc:                                                                                                   
       logit("error running command")

def switchAllOff(RAW_MESSAGE):
   ROOM_NUMBER=int(RAW_MESSAGE[1:3])
   UNIQUE_ID=PARSED_JSON['Room'][ROOM_NUMBER]['Switch'][0]['UNIQUE_ID']
   UNIQUE_ID_1=int(UNIQUE_ID[0:3]);
   UNIQUE_ID_2=int(UNIQUE_ID[3:6]);

   ser = serial.Serial("/dev/ttyAMA0", 19200)
   ser.write(C(254))
   ser.write(C(UNIQUE_ID_1))
   ser.write(C(UNIQUE_ID_2))
   ser.write(C(255))
   ser.write(C(242))
   ser.write(C(255))
   ser.write(C(0))
   ser.write(C(253))


def readStatusFile():
    global STATUS_JSON
    status_file=open(STATUS_FILE,'r')
    STATUS_JSON=status_file.read()

def publishCompleteStatus():
    ID=getID()
    readStatusFile()
    publishMQTT(ID+"/response/completeStatus",STATUS_JSON)


def learnBoards(RAW_MESSAGE):
   global MASTER_JSON 
   PARSED_JSON=json.loads(RAW_MESSAGE)
   REQUEST=PARSED_JSON['Request']

   if REQUEST=="setPanelId":
      NETWORK_ID_1=int(PARSED_JSON['networkid1'])
      NETWORK_ID_2=int(PARSED_JSON['networkid2'])
      GATEWAY_ID=int(PARSED_JSON['gatewayid'])
      ROOM_ID=int(PARSED_JSON['roomid'])
      PANEL_ID=int(PARSED_JSON['panelid'])
      
      ser = serial.Serial("/dev/ttyAMA0", 19200)
      ser.write(C(254))
      ser.write(C(255))
      ser.write(C(1))
      ser.write(C(1))
      ser.write(C(55))
      ser.write(C(NETWORK_ID_1))
      ser.write(C(NETWORK_ID_2))
      ser.write(C(GATEWAY_ID))
      ser.write(C(ROOM_ID))
      ser.write(C(PANEL_ID))
      ser.write(C(253))

   elif REQUEST=="setGatewayId":
      NETWORK_ID_1=int(PARSED_JSON['networkid1'])
      NETWORK_ID_2=int(PARSED_JSON['networkid2'])
      GATEWAY_ID=int(PARSED_JSON['gatewayid'])

      ser = serial.Serial("/dev/ttyAMA0", 19200)
      ser.write(C(254))
      ser.write(C(255))
      ser.write(C(252))
      ser.write(C(55))
      ser.write(C(NETWORK_ID_1))
      ser.write(C(NETWORK_ID_2))
      ser.write(C(GATEWAY_ID))
      ser.write(C(253))

   elif REQUEST=="setAutoMode":
      ROOM_ID=int(PARSED_JSON['roomid'])
      PANEL_ID=int(PARSED_JSON['panelid'])
      AUTOMODE=int(PARSED_JSON['automode'])

      ser = serial.Serial("/dev/ttyAMA0", 19200)
      ser.write(C(254))
      ser.write(C(255))
      ser.write(C(ROOM_ID))
      ser.write(C(PANEL_ID))
      ser.write(C(AUTOMODE))
      ser.write(C(253))


   elif REQUEST=="Learn":
      logit("Learning modules Started")
      LEARN_CFG_FILE="/home/pi/andy/cfg/masterJSON.cfg"
      data = {}
      data['Room'] = []
      json_data = json.dumps(data)
      learn_file=open(LEARN_CFG_FILE,'w')
      learn_file.write(json_data)
      learn_file.close()

      for Room in range(1,11): 
         logit("Scanning for Room " + str(Room))
         ser = serial.Serial("/dev/ttyAMA0", 19200)
         ser.write(C(254))
         ser.write(C(1))
         ser.write(C(Room))
         ser.write(C(255))
         ser.write(C(45))
         ser.write(C(253))
         time.sleep(3)

      CFG_FILE="/home/pi/andy/cfg/masterJSON.cfg"
      file = open(CFG_FILE, 'r')
      MASTER_JSON=file.read()

      os.system("python /home/pi/andy/master/createStatus.py")
      os.system("python /home/pi/andy/master/createMobileConfig.py")

      MOBILE_CFG="/home/pi/andy/cfg/mobile.cfg"
      STATUS_CFG="/home/pi/andy/cfg/statusJSON.cfg"

      target_mobile = open(MOBILE_CFG, 'r')
      MOBILE_JSON=target_mobile.read()
      MOBILE_PARSED_JSON=json.loads(MOBILE_JSON)

      target_status = open(STATUS_CFG, 'r')
      STATUS_JSON=target_status.read()
      STATUS_PARSED_JSON=json.loads(STATUS_JSON)

      configure_data = {}
      configure_data['MASTER_CFG'] = {"CONFIG":MOBILE_PARSED_JSON, "STATUS":STATUS_PARSED_JSON}

      configure_json_data = json.dumps(configure_data)
      publishMQTT("response/configure",configure_json_data)
      publishMQTT("response/adminControl","{\"Response\":\"Learn Completed\"}")

    
def publishPingMQTT():
    ID=getID()
    topic=ID+"/response/ping"
    message="ping successfull"
    client.publish(topic,message)

def publishMQTT(topic,message):
    try:
       client.publish(topic,message)
      # publish.single(topic,message, hostname=LOCAL)
    except socket.error as err:
       logit("socket.err")

def sceneProcess(SCENE_COMMANDS):
    PARSED_JSON=json.loads(SCENE_COMMANDS)
    COMMANDS=PARSED_JSON['Scene']
    for COMMAND_NUMBER in range(len(COMMANDS)):
        COMMAND_SINGLE=PARSED_JSON['Scene'][COMMAND_NUMBER]['Command']
        commandProcess(COMMAND_SINGLE)
        time.sleep(0.1)
         
def commandProcess(COMMAND):
    ROOM_NUMBER=int(COMMAND[1:3])
    SWITCH_NUMBER=int(COMMAND[4:6])
    OPERATION=COMMAND[6:9]
    BUTTON_NUMBER=PARSED_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['BUTTON_NUMBER']
    BUTTON_TYPE=PARSED_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['Type']
    UNIQUE_ID=PARSED_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['UNIQUE_ID']
    if BUTTON_TYPE=="Normal":
       BUTTON_COMMAND="L"
    elif BUTTON_TYPE=="Fan":
       BUTTON_COMMAND="F"
    elif BUTTON_TYPE=="Fan":
       BUTTON_COMMAND="F"
    elif BUTTON_TYPE=="Dimmer":
       BUTTON_COMMAND="D"
    elif BUTTON_TYPE=="Curtain":
       BUTTON_COMMAND="C"
    elif BUTTON_TYPE=="Bell":
       BUTTON_COMMAND="B"
    elif BUTTON_TYPE=="Scene":
       BUTTON_COMMAND="S"
   
    logit("Command Process "+BUTTON_COMMAND+ " " + BUTTON_NUMBER + " " + OPERATION + " " +UNIQUE_ID)
    rawCommandProcess(BUTTON_COMMAND,BUTTON_NUMBER,OPERATION,UNIQUE_ID)

def rawCommandProcess(BUTTON_TYPE,BUTTON,OPERATION,UNIQUE_ID):
   if BUTTON_TYPE=="D":
      if OPERATION=="ON":
         OPERATION_COMMAND=101
      elif OPERATION=="OF":
         OPERATION_COMMAND=0
      else:
         OPERATION_COMMAND=int(OPERATION)*10
      BUTTON_TYPE_COMMAND=248
   elif BUTTON_TYPE=="F":
      if OPERATION=="ON":
         OPERATION_COMMAND=101
      elif OPERATION=="OF":
         OPERATION_COMMAND=0
      else:
         OPERATION_COMMAND=int(OPERATION)*10
      BUTTON_TYPE_COMMAND=249
   elif BUTTON_TYPE=="L":
      if OPERATION=="ON":
         OPERATION_COMMAND=1
      else:
         OPERATION_COMMAND=0
      BUTTON_TYPE_COMMAND=250
   elif BUTTON_TYPE=="B":
      if OPERATION=="ON":
         OPERATION_COMMAND=1
      else:
         OPERATION_COMMAND=0
      BUTTON_TYPE_COMMAND=250
   elif BUTTON_TYPE=="C":
      if OPERATION=="ON":
         OPERATION_COMMAND=1
      elif OPERATION=="OF":
         OPERATION_COMMAND=2
      elif OPERATION=="ST":
         OPERATION_COMMAND=0
      BUTTON_TYPE_COMMAND=244
   elif BUTTON_TYPE=="S":
      if OPERATION=="ON":
         OPERATION_COMMAND=101
      else:
         OPERATION_COMMAND=0
      BUTTON_TYPE_COMMAND=245

   UNIQUE_ID_1=int(UNIQUE_ID[0:3]);
   UNIQUE_ID_2=int(UNIQUE_ID[3:6]);
   UNIQUE_ID_3=int(UNIQUE_ID[6:9]);
   logit("Raw Frame: 254 " + str(UNIQUE_ID_1) + " " + str(UNIQUE_ID_2) + " " + str(UNIQUE_ID_3) + " " + str(BUTTON_TYPE_COMMAND) + " " + str(BUTTON) + " " + str(OPERATION_COMMAND) + "  253")
   ser = serial.Serial("/dev/ttyAMA0", 19200)
   ser.write(C(254))
   ser.write(C(UNIQUE_ID_1))
   ser.write(C(UNIQUE_ID_2))
   ser.write(C(UNIQUE_ID_3))
   ser.write(C(BUTTON_TYPE_COMMAND))
   ser.write(C(int(BUTTON)))
   ser.write(C(OPERATION_COMMAND))
   ser.write(C(253))

def C( num ):
    return struct.pack('!B',num)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set("andy","andy!@#$%")
try:
  client.connect(SERVER, 1883, 60)
except socket.error as err:
  logit("Socket Error")
client.loop_forever()
