import glob, os, re
from dxlogmond import Parser
from bson import json_util
import json
import time
from config import ACCOUNTS
from dexlib import get_api_access_token
from dexlib import get_devices
from dexlib import push_device_data

all_rows = []
acc_tokens = []
devices = []

for acc in ACCOUNTS:
    acc_tokens.append(get_api_access_token(acc[0], acc[1]))

for acc in acc_tokens:
    devices+=get_devices(acc[2])

for d in devices:
    if(d['id']['id'] == "286d8150-8452-11e8-9046-d95bc5a50e6d"):
	status_device = d

files = glob.glob("/var/log/*-messages")

for f in files:
    aa=re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-messages$",f)
    if(aa == None):
        files.remove(f)

d_statuses = []
d_off_statuses = []
total_vpns = len(files)
online_count = -1
offline_count = -1

print("Processing one time log files...")

for f in files:
    print("Processing file: ", f)
    d_on_off_status = False
    d_off_status = False
    read_status = False
    with open(f, 'r') as df:
        for l in df:
            try:
                fields = l.split()
                fields = [(x.split("=")[0], x.split("=")[1].strip("\""))
                        for x in fields if "=" in x]

                fields = dict(fields)
                if(fields['log_subtype'].lower() == "system"):
<<<<<<< HEAD
=======
                    if(fields['status'].lower() == "established"):
                        d_on_off_status = not d_on_off_status
                        read_status = True
>>>>>>> 434e00027f6afd027c93df66f8b85cd58e48d2e6
                    if(fields['status'].lower() == "terminated"):
                        d_on_off_status = not d_on_off_status
			d_off_status = not d_off_status
                        read_status = True
            except:
                pass
        
    if(read_status == True):
        d_statuses.append(int(d_on_off_status))
	d_off_statuses.append(int(d_off_status))

online_count = sum(d_statuses)
offline_count = sum(d_off_statuses)

for d in devices:
    if(d['id']['id'] == "8d9a5f20-844e-11e8-9046-d95bc5a50e6d"):
        push_device_data(d, {
            "status": "",
            "message": "",
            "total_vpn": total_vpns,
            "vpn_online": total_vpns - sum(d_off_statuses),
            "vpn_offline": sum(d_off_statuses)
        })

print("Starting Loop.....")
while True:

    for f in files:
        with open(f, 'r') as lf:
            for line in lf:
		pass
        try:
            fields = line.split()
            fields = [(x.split("=")[0], x.split("=")[1].strip("\""))
                    for x in fields if "=" in x]

            fields = dict(fields)
            push_device_data(status_device, fields)

            if(fields['log_subtype'].lower() == "system"):
                if(fields['status'].lower() == "established"):
                    online_count = online_count + 1
                if(fields['status'].lower() == "terminated"):
                    offline_count = offline_count - 1
                if(fields['status'].lower() != "successful"):
                    for d in devices:
                        if(d['id']['id'] == "8d9a5f20-844e-11e8-9046-d95bc5a50e6d"):
                            push_device_data(d, {
                                "status": fields['status'], 
                                "message": fields['message'],
                                "total_vpn": total_vpns,
                                "vpn_online": online_count,
<<<<<<< HEAD
                                "vpn_offline": offline_count}
                            )
=======
                                "vpn_offline": offline_count})

            with open('/home/dxlroot/syslog/data/messages_parsed.json', 'a') as wf:
                wf.write(json.dumps(fields, default=json_util.default)+"\n")
>>>>>>> 434e00027f6afd027c93df66f8b85cd58e48d2e6
        except Exception as e:
            print(e)
            print(line)

    time.sleep(0.5)
    
