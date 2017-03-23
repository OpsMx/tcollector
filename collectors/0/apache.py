#!/usr/bin/python

import sys
import json
import time
import re
from collectors.etc import opsmxconf
from collectors.lib import utils
import traceback

# Change the Apache stats URL accordingly in 'opsmxconf.py'. Retain the "?auto" suffix.
url=opsmxconf.APACHE_CONFIG["base_url"]+"/server-status?auto"
username=opsmxconf.APACHE_CONFIG["username"]
password=opsmxconf.APACHE_CONFIG["password"]
if opsmxconf.OVERRIDE:
    COLLECTION_INTERVAL=opsmxconf.GLOBAL_COLLECTORS_INTERVAL
else:
    COLLECTION_INTERVAL=10

# if any impacting changes to this plugin kindly increment the plugin version here.
#PLUGIN_VERSION = "1"

# Setting this to true will alert you when there is a communication problem while posting plugin data to server
#HEARTBEAT = "true"


dict_reqdMet = {'Total Accesses':'apache.Activity_Total_Accesses',
                'Total kBytes'  :'apache.Activity_Total_Traffic',
                'CPULoad'       :'apache.Resource_Utilization_CPU_Load',
                'Uptime'        :'apache.Availability_Server_Uptime_sec',
                'ReqPerSec'     :'apache.Activity_Requests/min',
                'BytesPerSec'   :'apache.Activity_Bytes/min',
                'BytesPerReq'   :'apache.Activity_Bytes/req',
                'BusyWorkers'   :'apache.Resource_Utilization_Processes_Busy_Workers',
                'IdleWorkers'   :'apache.Resource_Utilization_Processes_Idle_Workers'
                }

counter_metrics={
                'apache.Activity_Type_Cleaning_Up': 0,
                'apache.Activity_Type_Closing_Connection': 0,
                'apache.Activity_Type_Starting_Up': 0,
                'apache.Activity_Type_Reading_Request': 0,
                'apache.Activity_Type_Sending_Reply': 0,
                'apache.Activity_Type_Keep_Alive': 0,
                'apache.Activity_Type_DNS_Lookup': 0,
                'apache.Activity_Type_Logging':0,
                'apache.Activity_Type_Gracefully_Finishing':0}

PYTHON_MAJOR_VERSION = sys.version_info[0]
# REQUESTS_INSTALLED = None
if PYTHON_MAJOR_VERSION == 3:
    import urllib
    import urllib.request as urlconnection
    from urllib.error import URLError, HTTPError
    from http.client import InvalidURL
elif PYTHON_MAJOR_VERSION == 2:
    import urllib2
    from urllib2 import HTTPError, URLError
    from httplib import InvalidURL

    
def metricCollector2(): #For Python 2.7
    try:
        if (username and password):
                password_mgr = urllib2.HTTPPasswordMgr()
                password_mgr.add_password(_realm, _url, _userName, _userPass)
                auth_handler = urllib2.HTTPBasicAuthHandler(password_mgr)
                opener = urllib2.build_opener(auth_handler)
                urllib2.install_opener(opener)
        response = urllib2.urlopen(url, timeout=10)
        ts=int(time.time())
        if response.getcode() == 200:
            byte_responseData = response.read()
            str_responseData = byte_responseData.decode('UTF-8')
            return (str_responseData,ts)
        else:
            utils.err('Error_code' + str(response.getcode()))
            return 1
    except HTTPError as e:
        utils.err('Error_code : HTTP Error ' + str(e.code))
        return 1
    except URLError as e:
        utils.err('Error_code : URL Error ' + str(e.reason))
        return 1
    except InvalidURL as e:
        utils.err('Error_code : Invalid URL')
        return 1
    except Exception as e:
        print traceback.format_exc()
        utils.err('Error: Exception occured in collecting data : ' + str(e))
        return 1

def metricCollector3(): # For Python 3
    try:
        if (username and password):
                password_mgr = urlconnection.HTTPPasswordMgr()
                password_mgr.add_password(_realm, _url, _userName, _userPass)
                auth_handler = urlconnection.HTTPBasicAuthHandler(password_mgr)
                opener = urlconnection.build_opener(auth_handler)
                urlconnection.install_opener(opener)
        response = urlconnection.urlopen(url, timeout=10)
        ts=int(time.time())
        if response.status == 200:
            byte_responseData = response.read()
            str_responseData = byte_responseData.decode('UTF-8')
            return (str_responseData,ts)
        else:
            utils.err('Error_code' + str(response.getcode()))
            return 1
    except HTTPError as e:
        utils.err('Error_code : HTTP Error ' + str(e.code))
        return 1
    except URLError as e:
        utils.err('Error_code : URL Error ' + str(e.reason))
        return 1
    except InvalidURL as e:
        utils.err('Error_code : Invalid URL')
        return 1
    except Exception as e:
        print traceback.format_exc()
        utils.err('Error: Exception occured in collecting data : ' + str(e))
        return 1

functions={
           2:metricCollector2,
           3:metricCollector3
           }

def counter(value):
    global counter_metrics
    if "I" in value:
        counter_metrics["apache.Activity_Type_Cleaning_Up"]+=1
    elif "C" in value:
        counter_metrics["apache.Activity_Type_Closing_Connection"]+=1
    elif "S" in value:
        counter_metrics["apache.Activity_Type_Starting_Up"]+=1
    elif "R" in value:
        counter_metrics["apache.Activity_Type_Reading_Request"]+=1
    elif "W" in value:
        counter_metrics["apache.Activity_Type_Sending_Reply"]+=1
    elif "K" in value:
        counter_metrics["apache.Activity_Type_Keep_Alive"]+=1
    elif "D" in value:
        counter_metrics["apache.Activity_Type_DNS_Lookup"]+=1
    elif "L" in value:
        counter_metrics["apache.Activity_Type_Logging"]+=1
    elif "G" in value:
        counter_metrics["apache.Activity_Type_Gracefully_Finishing"]+=1

def main():
    global counter_metrics
    while True:
        str_responseData=functions[PYTHON_MAJOR_VERSION]()
        try:
            listStatsData = str_responseData[0].split('\n')
            for eachStat in listStatsData:
                stats = eachStat.split(':')
                if str(stats[0]) in dict_reqdMet:
                    if str(stats[0].strip()) == "BytesPerSec" or str(stats[0].strip()) == "ReqPerSec":
                        value=round(float(str.strip(str(stats[1])))/60,5) # Converting Sec to Min.
                        print("{} {} {}".format(dict_reqdMet[str(stats[0])], str_responseData[1], value))
                    else:
                        print("{} {} {}".format(dict_reqdMet[str(stats[0])], str_responseData[1], str.strip(str(stats[1]))))
                    
                if str(stats[0].strip())=="Scoreboard":
                    counter(stats[1])
            for key, value in counter_metrics.items():
                print("{} {} {}".format(key,str_responseData[1], value))
            #dictApacheData['plugin_version'] = PLUGIN_VERSION
            #dictApacheData['heartbeat_required'] = HEARTBEAT
        except TypeError as e:
            utils.err('Type error in _parseStats')
        except Exception as e:
            utils.err('Exception in parse stats' + str(e))
        finally:
            sys.stdout.flush()
        time.sleep(COLLECTION_INTERVAL)

if __name__ == '__main__':
    sys.stdin.close()
    main()
 
