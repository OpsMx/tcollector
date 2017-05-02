#!/usr/bin/env python

import sys
import re
import time
import traceback
import os
from collectors.etc import opsmxconf
from collectors.lib import utils

try:
    import MySQLdb
except ImportError:
    utils.err("Error: Missing `MySQLb' module, please install it by running >'pip install MySQL-python'")
    sys.exit(1)


if opsmxconf.OVERRIDE:
    COLLECTION_INTERVAL=opsmxconf.GLOBAL_COLLECTORS_INTERVAL
else:
    COLLECTION_INTERVAL=10

mysqlhost=opsmxconf.MYSQL_CONFIG["ip"]
mysqlport=opsmxconf.MYSQL_CONFIG["port"]
mysqluser=opsmxconf.MYSQL_CONFIG["username"]
mysqlpasswd=opsmxconf.MYSQL_CONFIG["password"]
Extend=opsmxconf.MYSQL_CONFIG["extended"]
MYSQL_VARS = [
    'binlog_stmt_cache_size',
    'innodb_additional_mem_pool_size',
    'innodb_buffer_pool_size',
    'innodb_concurrency_tickets',
    'innodb_io_capacity',
    'innodb_log_buffer_size',
    'innodb_log_file_size',
    'innodb_open_files',
    'innodb_open_files',
    'join_buffer_size',
    'max_connections',
    'open_files_limit',
    'query_cache_limit',
    'query_cache_size',
    'query_cache_size',
    'read_buffer_size',
    'table_cache',
    'table_definition_cache',
    'table_open_cache',
    'thread_cache_size',
    'thread_cache_size',
    'thread_concurrency',
    'tmp_table_size',
]

MYSQL_PROCESS_STATES = {
    'closing_tables': 0,
    'copying_to_tmp_table': 0,
    'end': 0,
    'freeing_items': 0,
    'init': 0,
    'locked': 0,
    'login': 0,
    'none': 0,
    'other': 0,
    'preparing': 0,
    'reading_from_net': 0,
    'sending_data': 0,
    'sorting_result': 0,
    'statistics': 0,
    'updating': 0,
    'writing_to_net': 0,
}

MYSQL_STATUS_VARS = {
    'Aborted_clients': 'counter',
    'Aborted_connects': 'counter',
    'Binlog_cache_disk_use': 'counter',
    'Binlog_cache_use': 'counter',
    'Bytes_received': 'counter',
    'Bytes_sent': 'counter',
    'Connections': 'counter',
    'Created_tmp_disk_tables': 'counter',
    'Created_tmp_files': 'counter',
    'Created_tmp_tables': 'counter',
    'Innodb_buffer_pool_pages_data': 'gauge',
    'Innodb_buffer_pool_pages_dirty': 'gauge',
    'Innodb_buffer_pool_pages_free': 'gauge',
    'Innodb_buffer_pool_pages_total': 'gauge',
    'Innodb_buffer_pool_read_requests': 'counter',
    'Innodb_buffer_pool_reads': 'counter',
    'Innodb_checkpoint_age': 'gauge',
    'Innodb_checkpoint_max_age': 'gauge',
    'Innodb_data_fsyncs': 'counter',
    'Innodb_data_pending_fsyncs': 'gauge',
    'Innodb_data_pending_reads': 'gauge',
    'Innodb_data_pending_writes': 'gauge',
    'Innodb_data_read': 'counter',
    'Innodb_data_reads': 'counter',
    'Innodb_data_writes': 'counter',
    'Innodb_data_written': 'counter',
    'Innodb_deadlocks': 'counter',
    'Innodb_history_list_length': 'gauge',
    'Innodb_ibuf_free_list': 'gauge',
    'Innodb_ibuf_merged_delete_marks': 'counter',
    'Innodb_ibuf_merged_deletes': 'counter',
    'Innodb_ibuf_merged_inserts': 'counter',
    'Innodb_ibuf_merges': 'counter',
    'Innodb_ibuf_segment_size': 'gauge',
    'Innodb_ibuf_size': 'gauge',
    'Innodb_lsn_current': 'counter',
    'Innodb_lsn_flushed': 'counter',
    'Innodb_max_trx_id': 'counter',
    'Innodb_mem_adaptive_hash': 'gauge',
    'Innodb_mem_dictionary': 'gauge',
    'Innodb_mem_total': 'gauge',
    'Innodb_mutex_os_waits': 'counter',
    'Innodb_mutex_spin_rounds': 'counter',
    'Innodb_mutex_spin_waits': 'counter',
    'Innodb_os_log_pending_fsyncs': 'gauge',
    'Innodb_pages_created': 'counter',
    'Innodb_pages_read': 'counter',
    'Innodb_pages_written': 'counter',
    'Innodb_row_lock_time': 'counter',
    'Innodb_row_lock_time_avg': 'gauge',
    'Innodb_row_lock_time_max': 'gauge',
    'Innodb_row_lock_waits': 'counter',
    'Innodb_rows_deleted': 'counter',
    'Innodb_rows_inserted': 'counter',
    'Innodb_rows_read': 'counter',
    'Innodb_rows_updated': 'counter',
    'Innodb_s_lock_os_waits': 'counter',
    'Innodb_s_lock_spin_rounds': 'counter',
    'Innodb_s_lock_spin_waits': 'counter',
    'Innodb_uncheckpointed_bytes': 'gauge',
    'Innodb_unflushed_log': 'gauge',
    'Innodb_unpurged_txns': 'gauge',
    'Innodb_x_lock_os_waits': 'counter',
    'Innodb_x_lock_spin_rounds': 'counter',
    'Innodb_x_lock_spin_waits': 'counter',
    'Key_blocks_not_flushed': 'gauge',
    'Key_blocks_unused': 'gauge',
    'Key_blocks_used': 'gauge',
    'Key_read_requests': 'counter',
    'Key_reads': 'counter',
    'Key_write_requests': 'counter',
    'Key_writes': 'counter',
    'Max_used_connections': 'gauge',
    'Open_files': 'gauge',
    'Open_table_definitions': 'gauge',
    'Open_tables': 'gauge',
    'Opened_files': 'counter',
    'Opened_table_definitions': 'counter',
    'Opened_tables': 'counter',
    'Qcache_free_blocks': 'gauge',
    'Qcache_free_memory': 'gauge',
    'Qcache_hits': 'counter',
    'Qcache_inserts': 'counter',
    'Qcache_lowmem_prunes': 'counter',
    'Qcache_not_cached': 'counter',
    'Qcache_queries_in_cache': 'counter',
    'Qcache_total_blocks': 'counter',
    'Questions': 'counter',
    'Select_full_join': 'counter',
    'Select_full_range_join': 'counter',
    'Select_range': 'counter',
    'Select_range_check': 'counter',
    'Select_scan': 'counter',
    'Slave_open_temp_tables': 'gauge',
    'Slave_retried_transactions': 'counter',
    'Slow_launch_threads': 'counter',
    'Slow_queries': 'counter',
    'Sort_merge_passes': 'counter',
    'Sort_range': 'counter',
    'Sort_rows': 'counter',
    'Sort_scan': 'counter',
    'Table_locks_immediate': 'counter',
    'Table_locks_waited': 'counter',
    'Table_open_cache_hits': 'counter',
    'Table_open_cache_misses': 'counter',
    'Table_open_cache_overflows': 'counter',
    'Threadpool_idle_threads': 'gauge',
    'Threadpool_threads': 'gauge',
    'Threads_cached': 'gauge',
    'Threads_connected': 'gauge',
    'Threads_created': 'counter',
    'Threads_running': 'gauge',
    'Uptime': 'gauge',
}

MYSQL_INNODB_STATUS_VARS = {
    'active_transactions': 'gauge',
    'current_transactions': 'gauge',
    'file_reads': 'counter',
    'file_system_memory': 'gauge',
    'file_writes': 'counter',
    'innodb_lock_structs': 'gauge',
    'innodb_lock_wait_secs': 'gauge',
    'innodb_locked_tables': 'gauge',
    'innodb_sem_wait_time_ms': 'gauge',
    'innodb_sem_waits': 'gauge',
    'innodb_tables_in_use': 'gauge',
    'lock_system_memory': 'gauge',
    'locked_transactions': 'gauge',
    'log_writes': 'counter',
    'page_hash_memory': 'gauge',
    'pending_aio_log_ios': 'gauge',
    'pending_buf_pool_flushes': 'gauge',
    'pending_chkp_writes': 'gauge',
    'pending_ibuf_aio_reads': 'gauge',
    'pending_log_writes':'gauge',
    'queries_inside': 'gauge',
    'queries_queued': 'gauge',
    'read_views': 'gauge',
}

MYSQL_INNODB_STATUS_MATCHES = {
    # 0 read views open inside InnoDB
    'read views open inside InnoDB': {
        'read_views': 0,
    },
    # 5635328 OS file reads, 27018072 OS file writes, 20170883 OS fsyncs
    ' OS file reads, ': {
        'file_reads': 0,
        'file_writes': 4,
    },
    # ibuf aio reads: 0, log i/o's: 0, sync i/o's: 0
    'ibuf aio reads': {
        'pending_ibuf_aio_reads': 3,
        'pending_aio_log_ios': 6,
        'pending_aio_sync_ios': 9,
    },
    # Pending flushes (fsync) log: 0; buffer pool: 0
    'Pending flushes (fsync)': {
        'pending_buf_pool_flushes': 7,
    },
    # 16086708 log i/o's done, 106.07 log i/o's/second
    " log i/o's done, ": {
        'log_writes': 0,
    },
    # 0 pending log writes, 0 pending chkp writes
    ' pending log writes, ': {
        'pending_log_writes': 0,
        'pending_chkp_writes': 4,
    },
    # Page hash           2302856 (buffer pool 0 only)
    'Page hash    ': {
        'page_hash_memory': 2,
    },
    # File system         657820264     (812272 + 657007992)
    'File system    ': {
        'file_system_memory': 2,
    },
    # Lock system         143820296     (143819576 + 720)
    'Lock system    ': {
        'lock_system_memory': 2,
    },
    # 0 queries inside InnoDB, 0 queries in queue
    'queries inside InnoDB, ': {
        'queries_inside': 0,
        'queries_queued': 4,
    },
    # --Thread 139954487744256 has waited at dict0dict.cc line 472 for 0.0000 seconds the semaphore:
    'seconds the semaphore': {
        'innodb_sem_waits': lambda row, stats: stats['innodb_sem_waits'] + 1,
        'innodb_sem_wait_time_ms': lambda row, stats: int(row[9]) * 1000,
    },
    # mysql tables in use 1, locked 1
    'mysql tables in use': {
        'innodb_tables_in_use': lambda row, stats: stats['innodb_tables_in_use'] + int(row[4]),
        'innodb_locked_tables': lambda row, stats: stats['innodb_locked_tables'] + int(row[6]),
    },
    "------- TRX HAS BEEN": {
        "innodb_lock_wait_secs": lambda row, stats: stats['innodb_lock_wait_secs'] + int(row[5]),
    },
}

ACTIVE_METRICS=['aborted_connects','bytes_received','bytes_sent','com_change_db',
                'com_load','innodb_buffer_pool_reads',
                'innodb_buffer_pool_write_requests','innodb_buffer_pool_pages_flushed',
                'max_used_connections','connections',
                'uptime','responsetime']

def now():
    return int(time.time())

def get_mysql_conn():
    try:
        conn= MySQLdb.connect(host=mysqlhost, port=mysqlport, user=mysqluser, passwd=mysqlpasswd)
        return conn
    except MySQLdb.Error:
        utils.err("Error: Not able to connect to host: "+mysqlhost)
        return None

def mysql_query(conn, query):
    try:
        curs = conn.cursor(MySQLdb.cursors.DictCursor)
        curs.execute(query)
        return curs
    except MySQLdb.OperationalError, (errcode):
        #if errcode != 2006:  # "MySQL server has gone away"
            #utils.err("MySQL server has gone away")
        raise
              
def fetch_mysql_variables(conn):
    global MYSQL_VARS
    try:
        result = mysql_query(conn, 'SHOW GLOBAL VARIABLES')
    except Exception as e:
        utils.err("Error: At fetch_mysql_variables method::"+str(e))
        return None
    variables = {}
    for row in result.fetchall():
        if row['Variable_name'] in MYSQL_VARS:
            variables[row['Variable_name']] = row['Value']
    return (variables,now())

def fetch_mysql_status(conn):
    try:
        result = mysql_query(conn, 'SHOW GLOBAL STATUS')
    except Exception as e:
        utils.err("Error: At fetch_mysql_status method::"+str(e))
        return None
    status = {}
    for row in result.fetchall():
        status[row['Variable_name']] = row['Value']
    # calculate the number of unpurged txns from existing mysqlvars
    if 'Innodb_max_trx_id' in status:
        status['Innodb_unpurged_txns'] = int(status['Innodb_max_trx_id']) - int(status['Innodb_purge_trx_id'])

    if 'Innodb_lsn_last_checkpoint' in status:
        status['Innodb_uncheckpointed_bytes'] = int(status['Innodb_lsn_current'])- int(status['Innodb_lsn_last_checkpoint'])

    if 'Innodb_lsn_flushed' in status:
        status['Innodb_unflushed_log'] = int(status['Innodb_lsn_current']) - int(status['Innodb_lsn_flushed'])
    return (status,now())

def fetch_innodb_stats(conn):
    global MYSQL_INNODB_STATUS_MATCHES, MYSQL_INNODB_STATUS_VARS
    try:
        result = mysql_query(conn, 'SHOW ENGINE INNODB STATUS')
    except Exception as e:
        utils.err("Error: At fetch_innodb_stats method::"+str(e))
        return None
    row=result.fetchone()
    status=row['Status']
    stats=dict.fromkeys(MYSQL_INNODB_STATUS_VARS.keys(), 0)

    for line in status.split("\n"):
        line = line.strip()
        row  = re.split(r' +', re.sub(r'[,;] ', ' ', line))
        if line == '': continue
        # ---TRANSACTION 144324402462, not started
        # ---TRANSACTION 144324402468, ACTIVE 0 sec committing
        if line.find("---TRANSACTION") != -1:
            stats['current_transactions'] += 1
            if line.find("ACTIVE") != -1:
                stats['active_transactions'] += 1
        # LOCK WAIT 228 lock struct(s), heap size 46632, 65 row lock(s), undo log entries 1
        # 205 lock struct(s), heap size 30248, 37 row lock(s)
        elif line.find("lock struct(s)") != -1:
            if line.find("LOCK WAIT") != -1:
                stats['innodb_lock_structs'] += int(row[2])
                stats['locked_transactions'] += 1
            else:
                stats['innodb_lock_structs'] += int(row[0])
        else:
            for match in MYSQL_INNODB_STATUS_MATCHES:
                if line.find(match) == -1: continue
                for key in MYSQL_INNODB_STATUS_MATCHES[match]:
                    value = MYSQL_INNODB_STATUS_MATCHES[match][key]
                    if type(value):
                        stats[key] = 0
                    elif type(value) is int:
                        stats[key] = int(row[value])
                    else:
                        stats[key] = value(row, stats)
                break
    return (stats,now())

def fetch_mysql_process_states(conn):
    global MYSQL_PROCESS_STATES
    try:
        result = mysql_query(conn, 'SHOW PROCESSLIST')
    except Exception as e:
        utils.err("Error: At fetch_mysql_process_states method::"+str(e))
        return None
    states = MYSQL_PROCESS_STATES.copy()
    for row in result.fetchall():
        state = row['State']
        if state == '' or state == None: state = 'none'
        state = re.sub(r'^(Table lock|Waiting for .*lock)$', "Locked", state)
        state = state.lower().replace(" ", "_")
        if state not in states: state = 'other'
        states[state] += 1
    return (states,now())

def fetch_mysql_master_stats(conn):
    try:
        result = mysql_query(conn, 'SHOW BINARY LOGS')
    except Exception as e:
        utils.err("Error: At 'fetch_mysql_master_stats' method::"+str(e))
        return None
    stats = {
        'binary_log_space': 0,
    }
    for row in result.fetchall():
        if 'File_size' in row and row['File_size'] > 0:
            stats['binary_log_space'] += int(row['File_size'])
    return (stats,now())

def fetch_mysql_response_times(conn):
    response_times = {}
    try:
        result = mysql_query(conn, """
            SELECT *
            FROM INFORMATION_SCHEMA.QUERY_RESPONSE_TIME
            WHERE `time` != 'TOO LONG'
            ORDER BY `time`
        """)
    except Exception as e:
        utils.err("Error: At 'fetch_mysql_response_times' method::"+str(e))
        return None

    for i in range(1, 14):
        row = result.fetchone()

        # fill in missing rows with zeros
        if not row:
            row = { 'count': 0, 'total': 0 }

        response_times[i] = {
            'time':  float(row['time']),
            'count': int(row['count']),
            'total': round(float(row['total']) * 1000000, 0),
        }
    return (response_times,now())


def get_query_exec_time_95th_us(conn):
    query_exec_time= {}
    metric = 'responsetime'
    # Fetches the 95th percentile query execution time and returns the value in milliseconds
    sql_95th_percentile = """SELECT n2.avg_us avg_us,
          IFNULL(SUM(n1.cnt)/NULLIF((SELECT COUNT(*) FROM performance_schema.events_statements_summary_by_digest), 0), 0) percentile
          FROM (SELECT COUNT(*) cnt, ROUND(avg_timer_wait/1000000) AS avg_us
          FROM performance_schema.events_statements_summary_by_digest
          GROUP BY avg_us) AS n1
          JOIN (SELECT COUNT(*) cnt, ROUND(avg_timer_wait/1000000) AS avg_us
          FROM performance_schema.events_statements_summary_by_digest
               GROUP BY avg_us) AS n2
               ON n1.avg_us <= n2.avg_us
               GROUP BY n2.avg_us
               HAVING percentile > 0.95
               ORDER BY percentile LIMIT 1"""
    try:
        result=mysql_query(conn, sql_95th_percentile)
        row = result.fetchone()
        value =float(row['avg_us']/1000)
        query_exec_time={ metric:value }
        return (query_exec_time,now())
        
    except Exception as e:
        utils.err("Error: At 'get_query_exec_time_95th_us' method::"+str(e))
        return None
    
def printmetric(metric, ts, value, tags=""):
    if metric in ACTIVE_METRICS:
        print "mysql.{} {} {}".format(metric, ts, value)
    elif Extend:
        print "mysql.{} {} {}".format(metric, ts, value)

def main():
    while True:
        conn=get_mysql_conn()
        if conn:
            mysql_status = fetch_mysql_status(conn)
            master_stats = fetch_mysql_master_stats(conn)   
            mysql_exectime = get_query_exec_time_95th_us(conn)
            mysql_process_states = fetch_mysql_process_states(conn)
            mysql_innodb = fetch_innodb_stats(conn)
            mysql_variables = fetch_mysql_variables(conn)
            mysql_resp_times = fetch_mysql_response_times(conn)
            if mysql_status:
                for metric , value in mysql_status[0].iteritems():
                    try:
                        printmetric(metric.lower(),mysql_status[1],float(value))
                    except:
                        pass
                     
            if master_stats:
                for metric , value in master_stats[0].iteritems():
                    try:
                        printmetric(metric.lower(),master_stats[1], float(value))
                    except:
                        pass
                            
            if mysql_exectime:
                for metric , value in mysql_exectime[0].iteritems():
                    try:
                        printmetric(metric.lower(),mysql_exectime[1], float(value)) 
                    except:
                        pass
                                           
            if mysql_innodb:
                for metric , value in mysql_innodb[0].iteritems():
                    try:
                        printmetric(metric.lower(),mysql_innodb[1], float(value))
                    except:
                        pass
                              
            if mysql_process_states:
                for metric , value in mysql_process_states[0].iteritems():
                    try:
                        printmetric(metric.lower(),mysql_process_states[1], float(value))
                    except:
                        pass
                            
            if mysql_variables:
                for metric , value in mysql_variables[0].iteritems():
                    try:
                        printmetric(metric.lower(),mysql_variables[1], float(value)) 
                    except:
                        pass 
                                    
            if mysql_resp_times:
                for metric , value in mysql_resp_times[0].iteritems():
                    try:
                        printmetric(metric.lower(),mysql_resp_times[0], float(value))
                    except:
                        pass
                                   
        sys.stdout.flush()
        conn.close()     
        time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
    sys.stdin.close()
    main()
    
        
        

 