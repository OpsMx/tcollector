#!/usr/bin/python

import sys
import time
import traceback
import os
import socket
from collectors.etc import opsmxconf
from collectors.lib import utils

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    utils.err("Error: Missing `psycopg2' module, please install")
    sys.exit(1)

if opsmxconf.OVERRIDE:
    COLLECTION_INTERVAL=opsmxconf.GLOBAL_COLLECTORS_INTERVAL
else:
    COLLECTION_INTERVAL=10

postgresdb=opsmxconf.POSTGRESS_CONFIG["db"]
postgresuser=opsmxconf.POSTGRESS_CONFIG["username"]
postgrespasswd=opsmxconf.POSTGRESS_CONFIG["password"]
postgreshost=opsmxconf.POSTGRESS_CONFIG["ip"]
port=opsmxconf.POSTGRESS_CONFIG["port"]

def now():
    return int(time.time())

def get_postgres_conn(postgresdb,postgresuser,postgrespasswd,postgreshost,port):
    try:
       conn = psycopg2.connect(user=postgresuser, password=postgrespasswd, host=postgreshost, port=port)
       return conn
    except:
        utils.err("There was a problem in connecting to the host : "+postgreshost)

def get_postgres_statics(conn):
    try:
      cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
      stat_query =("SELECT pg_stat_database.*, pg_database_size"
                   " (pg_database.datname) AS size FROM pg_database JOIN"
                   " pg_stat_database ON pg_database.datname ="
                   " pg_stat_database.datname WHERE pg_stat_database.datname"
                   " NOT IN ('template0', 'template1', 'postgres')")
      cursor.execute(stat_query)
      ts = now()
      stats = cursor.fetchall()
      # datid |  datname   | numbackends | xact_commit | xact_rollback | blks_read  |  blks_hit   | tup_returned | tup_fetched | tup_inserted | tup_updated | tup_deleted | conflicts | temp_files |  temp_bytes  | deadlocks | blk_read_time | blk_write_time | stats_reset | size
      result = {}
      for stat in stats:
           database = stat[1]
           result[database] = stat
           for database in result:
               for i in range(2,len(cursor.description)):
                   metric = cursor.description[i].name
                   value = result[database][i]
                   try:
                      if metric in ("stats_reset"):
                         continue
                         printmetric(metric,ts,value,database)
                      else:
                         printmetric(metric,ts,value,database)
                   except:
                         utils.err("Error")
                         
      # connections
      cursor.execute("SELECT datname, count(datname) FROM pg_stat_activity"
                   " GROUP BY pg_stat_activity.datname")
      ts = now()
      connections = cursor.fetchall()
      for database, connection in connections:
          metric="connections"
          value=connection
          printmetric(metric,ts,value,database)
    except:
      utils.err("Error: ",traceback.format_exc())
      
def printmetric(metric, ts, value, database,tags=""):
        try:
            print "postgres.{} {} {} database={}".format(metric, ts, value, database)
        except Exception:
            utils.err("Error: ",traceback.format_exc())

def main():
    while True:
        conn = get_postgres_conn(postgresdb,postgresuser,postgrespasswd,postgreshost,port)
        if conn:
            try:
                general_status= get_postgres_statics(conn)
            except Exception:
                utils.err("Error: ",traceback.format_exc())
                time.sleep(20) #Error wait time!
            finally:
                try:
                    conn.close()
                except: pass
        sys.stdout.flush()
        time.sleep(COLLECTION_INTERVAL)
                  
if __name__ == "__main__":
    sys.stdin.close()
    main()
