# -*- encoding: utf-8 -*-
from dxlogmond import Parser
from bson import json_util
import json
import time
from config import ACCOUNTS
from dxparserlib import get_api_access_token
from dxparserlib import get_devices
from dxparserlib import push_device_data
from dxparserlib import follow

all_rows = []
parser = Parser()
acc_tokens = []
devices = []

for acc in ACCOUNTS:
    acc_tokens.append(get_api_access_token(acc[0], acc[1]))
for acc in acc_tokens:
    devices.append(get_devices(acc[2]))

logfile = open("/var/log/secure", "r")
loglines = follow(logfile)

for line in loglines:
    try:
        fields = parser.parse(line)
        if("established" in fields["message"].lower()):
            fields['status'] = "Established"
            fields['ts'] = fields['timestamp']['$date']
            fields.pop('timestamp')
            fields.pop('pid')
            data = {}
            data['ts'] = fields['ts']
            data['values'] = {}
            data['values']['hostname'] = fields['hostname']
            data['values']['appname'] = fields['appname']
            data['values']['message'] = fields['message']
            fields.pop('ts')
            push_device_data(devices[0][0], fields)

            # Uncomment the below lines for writing the parsed data to file
            # with open('/home/dxlroot/syslog/data/parsed.json', 'a') as wf:
                # wf.write(json.dumps(data, default=json_util.default)+"\n")

        elif("disconnected" in fields["message"].lower()):
            fields['status'] = "Disconnected"
            fields['ts'] = fields['timestamp']
            fields.pop('timestamp')
            fields.pop('pid')
            data = {}
            data['ts'] = fields['ts']
            data['values'] = {}
            data['values']['hostname'] = fields['hostname']
            data['values']['appname'] = fields['appname']
            data['values']['message'] = fields['message']
            fields.pop('ts')
            push_device_data(devices[0][0], fields)

            # Uncomment the below lines for writing the parsed data to file
            # with open('/home/dxlroot/syslog/data/parsed.json', 'a') as wf:
                # wf.write(json.dumps(data, default=json_util.default)+"\n")

    except Exception as e:
        print(e)
        print(line)
