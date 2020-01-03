# -*- encoding: utf-8 -*-
import traceback
import json
import requests
from pysnmp.hlapi import SnmpEngine, nextCmd, CommunityData, ContextData
from pysnmp.hlapi import UdpTransportTarget, ObjectType, ObjectIdentity

from easysnmp import Session

import threading

from pyparsing import Word, alphas, Suppress, Combine, nums, string, Regex, Optional

from datetime import datetime
from config import BASE_URL

class Parser(object):
    # log lines don't include the year, but if we don't provide one, datetime.strptime will assume 1900
    ASSUMED_YEAR = str(datetime.now().year)

    def __init__(self):
        ints = Word(nums)

        # priority
       # priority = Suppress("<") + ints + Suppress(">")

        # timestamp
        month = Word(string.ascii_uppercase, string.ascii_lowercase, exact=3)
        day = ints
        hour = Combine(ints + ":" + ints + ":" + ints)

        timestamp = month + day + hour
        # a parse action will convert this timestamp to a datetime
        timestamp.setParseAction(lambda t: datetime.strptime(
            Parser.ASSUMED_YEAR + ' ' + ' '.join(t), '%Y %b %d %H:%M:%S'))

        # hostname
        hostname = Word(alphas + nums + "_-.")

        # appname
        appname = Word(alphas + "/-_.()")("appname") + (Suppress(
            "[") + ints("pid") + Suppress("]")) | (Word(alphas + "/-_.")("appname"))
        appname.setName("appname")

        # message
        message = Regex(".*")

        # pattern build
        # (add results names to make it easier to access parsed fields)
        self._pattern = timestamp("timestamp") + hostname("hostname") + \
            Optional(appname) + Suppress(':') + message("message")

    def parse(self, line):
        parsed = self._pattern.parseString(line)
        # fill in keys that might not have been found in the input string
        # (this could have been done in a parse action too, then this method would
        # have just been a two-liner)
        for key in 'appname pid'.split():
            if key not in parsed:
                parsed[key] = ''
        return parsed.asDict()



class SNMPThread(threading.Thread):
  def __init__(self, func, args):
    threading.Thread.__init__(self)
    self.args = args
    self.func = func

  def run(self):
  	self.func(*self.args)


def runSNMP(device, queue):
    data, status = get_snmp_data(device)
    queue.put((device, data, status))


"""
    Function: get_dashboards
    Purpose: To get dashboards for each user account
    Returns: List of dashboards
"""


def get_dashboards(api_access_token):
    dashboards = []
    headers = {
        "Content-Type": "application/json",
        "X-Authorization": "Bearer " + api_access_token
    }
    res = requests.get(
        BASE_URL + "/api/tenant/dashboards?limit=50",
        headers=headers
    )
    res = json.loads(res.content)
    dashboards += res["data"]

    # Add status variable
    dashboards = [dict(x, status=1) for x in dashboards if x['id']['entityType'].upper() in [
        "DASHBOARD"]]

    return dashboards


"""
    Function: push_device_dashboards
    Purpose: To push device dashboards for each user account
    Returns: None
"""


def push_device_dashboards(devices, dasbhoards):
    data = {}
    for device in devices:
        device_name = device['name']
        for db in dasbhoards:
            if(device_name == db['name']):
                data[device_name] = BASE_URL + "/dashboards/"+db['id']['id']

    for device in devices:
        if(device['type'].upper() == "DX-DETAILS"):
            push_device_data(device, data)

    return None


"""
    Function: get_api_access_token
    Purpose: To get accesstoken for a user account
    Returns: Email, Password, Token
"""


def get_api_access_token(email, password):
    try:
        res = requests.post(
            BASE_URL + "/api/auth/login",
            data=json.dumps({
                "username": email,
                "password": password
            })
        )
        res = json.loads(res.content)
        return (email, password, res['token'])
    except Exception as e:
        print("--- API Access Token Error ---")
        print(res)
        print(e)
        print("--- API Access Token Error End ---")
        return (email, password, "")


"""
    Function: get_devices_access_token
    Purpose: To get device access toekn for each device
    Returns: List of devices updated with access token
"""


def get_devices_access_token(devices, api_access_token):
    updated_devices_list = []
    headers = {
        "Content-Type": "application/json",
        "X-Authorization": "Bearer "+api_access_token
    }
    for device in devices:
        res = requests.get(
            BASE_URL + "/api/device/" +
            str(device['id']['id']) + "/credentials",
            headers=headers
        )
        device["device_access_token"] = json.loads(res.content)[
            'credentialsId']
        updated_devices_list.append(device)

    return updated_devices_list


"""
    Function: get_server_attributes
    Purpose: To get server attributes for each device or a list of devices
    Returns: List of devices with server attributes
"""


def get_device_server_attributes(devices, api_access_token):
    updated_devices_list = []
    headers = {
        "Content-Type": "application/json",
        "X-Authorization": "Bearer "+api_access_token
    }
    for device in devices:
        if(device["type"].upper() == "DX-SNMP"):
            res = requests.get(
                BASE_URL + "/api/plugins/telemetry/DEVICE/" +
                str(device['id']['id']) + '/values/attributes/SERVER_SCOPE',
                headers=headers
            )

            attr_dev = {}
            for attr in json.loads(res.content):
                if(attr['key'].lower() == 'ip'):
                    attr_dev["host_name"] = attr['value']
                elif(attr['key'].lower() == 'port'):
                    attr_dev["port"] = int(attr['value'].strip())
                elif(attr['key'].lower() == 'community'):
                    attr_dev["community"] = attr['value']
                elif(attr['key'].lower() == 'snmp_version'):
                    attr_dev["snmp_version"] = int(attr['value'])
                elif(attr['key'].lower() == 'oid'):
                    attr_dev["oid"] = attr['value']
                elif(attr['key'].lower() == 'time_interval'):
                    attr_dev["time_interval"] = int(attr['value'])

            device["attributes"] = attr_dev
        updated_devices_list.append(device)

    return updated_devices_list


"""
    Function: get_devices
    Purpose: To get devices for each user account
    Returns: List of devices
"""


def get_devices(api_access_token):
    devices = []
    headers = {
        "Content-Type": "application/json",
        "X-Authorization": "Bearer " + api_access_token
    }
    res = requests.get(
        BASE_URL + "/api/tenant/devices?limit=500",
        headers=headers
    )
    res = json.loads(res.content)
    devices += res["data"]

    # Add status variable
    # devices = [dict(x, status=1) for x in devices if x['type'].upper() in [
    #     "DX-SNMP", "DX-STATUS", "DX-DETAILS", "DX-LOG"]]

    print(" --- Getting Device Accesstokens ---")
    devices = get_devices_access_token(devices, api_access_token)
    print(" --- Successfully Acquired Device Accesstokens ---")
    print(" --- Getting Device Server Attributes ---")
    devices = get_device_server_attributes(devices, api_access_token)
    print(" --- Successfully Acquired Device Server Attributes ---")
    return devices


"""
    Function: get_snmp_data
    Purpose: To get snmp data for a device
    Returns: List of SNMP data points
"""


def get_snmp_data(device):
    try:
        device_data = []
        if(device["type"].upper() == 'DX-SNMP'):
            community = device["attributes"]["community"]
            host_name = device["attributes"]["host_name"]
            port = device["attributes"]["port"]
            oids = device["attributes"]["oid"]
            if (device["attributes"]["snmp_version"] == 1):
                snmp_version = 0
            elif (device["attributes"]["snmp_version"] == 2):
                snmp_version = 1

            if(host_name != ""):
                if(oids != ""):
                    if(community != ""):
                        if(snmp_version != ""):
                            print("--- Reading SNMP Device Data ---")

                            for (errorIndication,
                                 errorStatus,
                                 errorIndex,
                                 varBinds) in nextCmd(SnmpEngine(),
                                                      CommunityData(
                                     community, mpModel=snmp_version),
                                    UdpTransportTarget(
                                     (host_name, port)),
                                    ContextData(),
                                    ObjectType(ObjectIdentity(oids))):

                                    if errorIndication:
                                        print("--- Error: " +
                                              str(errorIndication)+" ---")
                                        return device_data, 1
                                    elif errorStatus:
                                        print("--- Error ---")
                                        print('%s at %s' % (errorStatus.prettyPrint(),
                                                            errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
                                        print("--- Error End ---")
                                        return device_data, 1
                                    else:
                                        for varBind in varBinds:
                                            data_point = [x.prettyPrint()
                                                          for x in varBind]
                                            device_data.append(
                                                {
                                                    data_point[0].split(":")[-1].replace(".", "_"): data_point[1]
                                                }
                                            )
                            print("--- Successfully Read SNMP Device Data ---")
                            return device_data, 0
                        else:
                            print(
                                'Device attribute missing or invalid: snmp_version')
                            return [], 1
                    else:
                        print('Device attribute missing or invalid: community')
                        return [], 1
                else:
                    print('Device attribute missing or invalid: oid')
                    return [], 1
            else:
                print('Device attribute missing or invalid: host_name')
                return [], 1
        else:
            print('Device not of type DX-SNMP')
            return [], 1
    except Exception as e:
        # print(device)
        print('Error occured while reading snmp device: ', device['id'], e)
        # traceback.print_tb(e.__traceback__)
        return device_data, 1


"""
    Function: push_device_data
    Purpose: To push data to server that is read from the device
    Returns: Status code of the response
"""


def push_device_data(device, data):
    if(data == []):
        return 404
    else:
        print("--- Pushing Device Data ---")
        res = requests.post(
            BASE_URL + "/api/v1/" +
            device["device_access_token"] + "/telemetry",
            data=json.dumps(data)
        )
        print("--- Successfully Pushed Device Data ---")
        return res.status_code


"""
    Function: update_device_online_status
    Purpose: To update device online status data
    Returns: List of devices
"""


def update_device_online_status(devices):
    print("--- Update Device Online Status ---")

    for device in devices:
        if(device['type'].upper() == 'DX-STATUS'):
            devices_online = sum(list(map(lambda x: 1 if (
                x['type'] == 'DX-SNMP' and x['tenantId']['id'] == device['tenantId']['id'] and x['status'] == 0) else 0, devices)))
            devices_offline = sum(list(map(lambda x: 1 if (
                x['type'] == 'DX-SNMP' and x['tenantId']['id'] == device['tenantId']['id'] and x['status'] != 0) else 0, devices)))
            total_devices = devices_online + devices_offline
            device['devices_online'] = devices_online
            device['devices_offline'] = devices_offline
            device['total_devices'] = total_devices
            device['device_statuses'] = []
            for d in devices:
                if(d['type'].upper() != 'DX-STATUS'):
                    tstatus = 'ONLINE' if d['status'] == 0 else 'OFFLINE'
                    device['device_statuses'].append({
                        'name': d['name'],
                        'value': tstatus
                    })

    print("--- Successfully Updated Device Online Status ---")
    return devices


"""
    Function: push_device_online_status
    Purpose: To push device online status data to server
    Returns: Status code of the response
"""


def push_device_online_status(devices):
    print("--- Pushing Device Online Status ---")
    for device in devices:
        if(device['type'].upper() == 'DX-STATUS'):
            data = {
                'devices_online': device['devices_online'],
                'devices_offline': device['devices_offline'],
                'total_devices': device['total_devices']
            }
            for device_status in device['device_statuses']:
                data[device_status['name'].replace(
                    " ", "_")] = device_status['value']
            push_device_data(device, data)

    print("--- Successfully Pushed Device Online Status ---")
