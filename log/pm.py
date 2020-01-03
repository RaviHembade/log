import os, glob
from dexlib import Parser
from bson import json_util
import json
import time
from config import ACCOUNTS
from dexlib import get_api_access_token
from dexlib import get_devices
from dexlib import push_device_data

def get_token_devices():
    devices = []
    acc_tokens = []
    for user, pwd in ACCOUNTS:
        acc_tokens.append(get_api_access_token(user, pwd))
    for _, _, token in acc_tokens:
        devices += get_devices(token)
    return devices, acc_tokens


if __name__ == "__main__":
    all_rows = []
    acc_tokens = []
    devices = []

    devices, acc_tokens = get_token_devices()
    devices = [d for d in devices if d['type'] == 'DX-LOG']

    # # files = glob.glob("/var/log/*-messages")
    files = glob.glob("data/msg_logs/*-messages")

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
                        if(fields['status'].lower() == "established"):
                            d_on_off_status = not d_on_off_status
                            read_status = True
                        if(fields['status'].lower() == "terminated"):
                            d_on_off_status = not d_on_off_status
                            d_off_status = not d_off_status
                            read_status = True
                except:
                    pass

        if(read_status == True):
            d_statuses.append(int(d_on_off_status))
        else:
            d_off_statuses.append(int(d_off_status))

    online_count = total_vpns
    offline_count = sum(d_off_statuses)
    print(online_count, offline_count)
    # for d in devices:
    #     if(d['id']['id'] == logger_device['id']['id']):
    #         push_device_data(d, {
    #             "status": "",
    #             "message": "",
    #             "total_vpn": total_vpns,
    #             "vpn_online": total_vpns - sum(d_off_statuses),
    #             "vpn_offline": sum(d_off_statuses)
    #         })

    print("Starting Loop.....")
    while True:

        for f in files:
            for d in devices:
                if(d['name'] == f.split('-')[0].split("/")[-1]):
                    log_device = d
                    # print("Log Device: ", log_device)


            try:
                with open(f, 'r') as lf:
                    for line in lf:
                        pass

                fields = line.split()
                fields = [(x.split("=")[0], x.split("=")[1].strip("\""))
                        for x in fields if "=" in x]

                fields = dict(fields)
                fields["log_"+f.split('/')[-1].split("-")
                    [0].replace('.', '_')] = "ONLINE"
                push_device_data(log_device, fields)

                if(fields['log_subtype'].lower() == "system"):
                    if(fields['status'].lower() == "established"):
                        online_count = online_count + 1
                    if(fields['status'].lower() == "terminated"):
                        offline_count = offline_count - 1
                        fields = dict()
                        fields["log_"+f.split('/')[-1].split("-")
                            [0].replace('.', '_')] = "OFFLINE"
                        push_device_data(log_device, fields)
                    if(fields['status'].lower() != "successful"):
                        print(total_vpns, online_count, offline_count)
                # for d in devices:
                #     if(d['id']['id'] == log_device['id']['id']):
                #         push_device_data(d, {
                #             "status": fields['status'],
                #             "message": fields['message'],
                #             "total_vpn": total_vpns,
                #             "vpn_online": online_count,
                #             "vpn_offline": offline_count})

                #with open('/home/dxlroot/syslog/data/messages_parsed.json', 'a') as wf:
                #    wf.write(json.dumps(fields, default=json_util.default)+"\n")
            except Exception as e:
                print(e)
                # print(line)

        time.sleep(1)
