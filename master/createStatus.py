import json
import os
CFG_FILE="/home/pi/andy/cfg/masterJSON.cfg"
STATUS_FILE="/home/pi/andy/cfg/statusJSON.cfg"

target = open(CFG_FILE, 'r')
MASTER_JSON=target.read()
PARSED_JSON=json.loads(MASTER_JSON)

data = {}
data['Room'] = []
for ROOM_NUMBER in range(len(PARSED_JSON['Room'])):
    data['Room'].append({'Switch':[]})
    for SWITCH_NUMBER in range(len(PARSED_JSON['Room'][ROOM_NUMBER]['Switch'])):
         CUR_TYPE=PARSED_JSON['Room'][ROOM_NUMBER]['Switch'][SWITCH_NUMBER]['Type']
         if ( CUR_TYPE == "Normal"):
            data['Room'][ROOM_NUMBER]['Switch'].append({"SwitchStatus":"OF"})
         elif ( CUR_TYPE == "Bell"):
            data['Room'][ROOM_NUMBER]['Switch'].append({"SwitchStatus":"OF"})
         elif ( CUR_TYPE == "Curtain"):
            data['Room'][ROOM_NUMBER]['Switch'].append({"SwitchStatus":"OF"})
         elif ( CUR_TYPE == "Scene"):
            data['Room'][ROOM_NUMBER]['Switch'].append({"SwitchStatus":"OF"})
         else:
            data['Room'][ROOM_NUMBER]['Switch'].append({"SwitchStatus":"OF","DimmerStatus": "1"})


json_data = json.dumps(data)
status_file=open(STATUS_FILE,'w')
status_file.write(json_data)
status_file.close()

os.system("systemctl restart andy_output")
os.system("systemctl restart andy_input_cloud")
os.system("systemctl restart andy_input_local")
