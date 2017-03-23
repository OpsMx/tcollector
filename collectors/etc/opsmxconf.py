#!/usr/bin/env python

'''
Author: OpsMx
Description: Configuration variables for the OpsMx scripts
'''

OVERRIDE=False  #'OVERRIDE' is useful to override script's collection interval time to 'GLOBAL_COLLECTORS_INTERVAL'
GLOBAL_COLLECTORS_INTERVAL=5

#For proc-cpu-mem script: Please select the process that needs to monitor
SERVICES={
          "apache"  : True,
          "mysql"   : False,
          "redis"   : False,
          "hbase"   : False,
          "tomcat"  : False,
          "httpd"   : False
        }
SNIFF_INTERVAL=10

#For apache script: Please specify apache's base URL, username and password(If requried)
APACHE_CONFIG={
               "username"   : None,                     #If there is no username, specify 'None'
               "password"   : None,                     #If there is no password, specify 'None'
               "base_url"   : "http://localhost:80"     #For example: http://localhost:80 or https://192.168.1.1:443
            }

#For Opsmx mysql script: Please specify following fields
MYSQL_CONFIG={
              "ip"          : "localhost",
              "port"        : 3306,
              "username"    : "root",  #If there is no username, specify 'None'
              "password"    : "123",   #If there is no password, specify 'None'
              "extended"    : False     #True=Pushes all metrics, False=Pushes seleted metrics 
              }


#For Opsmx postgress script: Please specify following fields
POSTGRESS_CONFIG={
                  "db"      : "postgress",
                  "username": None,         #If there is no username, specify 'None'
                  "password": None,         #If there is no password, specify 'None'
                  "ip"      : "localhost",
                  "port"    : 5432
                  }

