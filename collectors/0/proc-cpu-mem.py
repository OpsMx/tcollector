#!/usr/bin/env python
'''
Author: OpsMx
Description: Retrieving the memory and CPU utilization of selected process
'''
import logging
from logging.handlers import RotatingFileHandler
import os
import subprocess
import time
import threading
import traceback
import sys
import glob
import logging
from collectors.etc import opsmxconf
from collectors.lib import utils


DEFAULT_LOG="/var/log/proc-cpu-mem.log"
handler=RotatingFileHandler(DEFAULT_LOG, mode='a', maxBytes=20*1024*1024, backupCount=0, encoding=None, delay=0)
handler.setFormatter(logging.Formatter('%(asctime)s %(name)s[%(process)d] %(levelname)s: %(message)s'))
log=logging.getLogger('OpsMx-PROC_CPU_MEM')
levels={"debug":logging.DEBUG,
        "info":logging.INFO,
        "warning":logging.WARNING,
        "error":logging.ERROR,
        "critical":logging.CRITICAL}

def log_it(level,message):
    log.setLevel(levels[level])
    log.addHandler(handler)
    handler.setLevel(levels[level])
    if level=="info":    
        log.info(message)    
    elif level=="debug":
        log.debug(message)
    elif level=="warning":
        log.warning(message)
    elif level=="error":
        log.error(message)
    elif level=="critical":
        log.critical(message)

try:
    service_list=[service for service in opsmxconf.SERVICES.keys() if opsmxconf.SERVICES[service]]
    SNIFF_INTERVAL=opsmxconf.SNIFF_INTERVAL
    if opsmxconf.OVERRIDE:
        COLLECTOR_INTERVAL=opsmxconf.GLOBAL_COLLECTORS_INTERVAL
    else:
        COLLECTOR_INTERVAL=2
except:
    log_it("critical","There were error(s) in config. Please check 'opsmxconf.py'. Exiting..")
    sys.exit(1)

if not service_list:
    log_it("info","Please set 'True' for at least one service in 'opsmxconf.py'. Exiting..")
    sys.exit(1)


class PIDs(threading.Thread):
    def __init__(self,desired_process):
        threading.Thread.__init__(self)
        self.lock=threading.RLock()
        self.desired_process=desired_process
        self.pid_locations={
                   "httpd":"/var/run/httpd/httpd.pid",
                   "apache":"/var/run/apache2/apache2.pid",
                   "mysql":"/var/run/mysqld/mysqld.pid",
                   "redis":"/var/run/redis.pid",
                   "hbase":"/tmp/hbase*.pid"
                   }
        self.tomcat_cmd="ps aux | grep -e org.apache.catalina.startup.Bootstrap | grep -v grep | awk '{ print $2 }'"
        self.processIDs=dict() #KEY->PID  Value--> Service
    
    def getPIDs(self):
        with self.lock:
            pids=self.processIDs
        if pids:
            return pids #KEY==> PID Value==>[ServiceName, TCPport]
        else:
            return None
    
    def grepPorts(self,pids_list):
        ports=dict()
        for pid in pids_list:
            for line in subprocess.check_output("ss -tulpn | grep -w {}".format(pid),shell=True).split("\n"):
                if line:
                    part=line.split()
                    ports.setdefault(int(pid),part[4].split(":")[-1])
        return ports #KEY==> PID, Value==>Port
    
    def run(self):
        while True:
            tmp=dict()
            try:
                for service in self.desired_process:
                    if service=="tomcat":
                        for pid in subprocess.check_output(self.tomcat_cmd,shell=True).split():
                            tmp.setdefault(int(pid),[service,0])
                    else:
                        loc=glob.glob(self.pid_locations[service])
                        if loc:
                            with open(loc[0],'r') as f:
                                tmp.setdefault(int(f.read()),[service,0]) #KEY->PID  Value--> [Service,port]
                ports=self.grepPorts(tmp.keys())
                if not ports:
                    log_it("debug","ports not found. "+traceback.format_exc())
                    with self.lock:
                        self.processIDs=tmp
                    time.sleep(10)
                    continue
                for pids , port in ports.items():
                    try:
                        if port:
                            tmp[pids][1]=port
                        else:
                            tmp[pids][1]=0 # Means, this process is not listening on other port
                    except:
                        print traceback.format_exc(),"\n"
                        continue
            except:
                log_it("error","There was a problem while retrieving the PIDs of services. "+traceback.format_exc())
                time.sleep(10)
                continue
            with self.lock:
                self.processIDs=tmp
            time.sleep(30)

class CPU:
    def __init__(self,pids=[1]): #pids===> KEY->PID  Value--> Service
        self.pids=pids
        self.stats_iteration=list()
        
    def getCPU(self):
        pid_stats=dict()
        try:
            # This for loop should be light weight. 
            # NOTE: The CPU utilization of processes would not get the accurate results!
            for x in range(2):
                pid_cpu_stats=dict()
                with open("/proc/stat","r") as f:
                    tmp_cpu_line=f.readlines()[0].split()[1:]
                for pids in self.pids:
                    if os.path.exists("/proc/{}/stat".format(pids)):
                        with open("/proc/{}/stat".format(pids),'r') as f:
                            line=f.read()
                            #print "Proc CPU Line",pids,"===>",line.split()[13:17]
                            pid_cpu_stats.setdefault(pids,line.split()[13:17])
                           
                    else:
                        #print "Here==>",pids
                        pid_cpu_stats.setdefault(pids,[0])
                self.stats_iteration.append([tmp_cpu_line,pid_cpu_stats])
                time.sleep(COLLECTOR_INTERVAL)
        except:
            log_it("error","/proc read error. "+traceback.format_exc())
            return None
        total_cpu_in_interval=sum(map(int,self.stats_iteration[1][0]))-sum(map(int,self.stats_iteration[0][0]))
        #print "Total",total_cpu_in_interval
        for pid2 in self.stats_iteration[1][1]:
            pass2_pid_cpu=sum(map(float,self.stats_iteration[1][1][pid2]))
            pass1_pid_cpu=sum(map(float,self.stats_iteration[0][1][pid2]))
            pid_cpu_percent=  round((((pass2_pid_cpu-pass1_pid_cpu)/total_cpu_in_interval)*100),5)
            pid_stats[pid2]=[self.pids[pid2][0],self.pids[pid2][1],pid_cpu_percent]
        #print "PASS 1",self.stats_iteration[0]
        #print "PASS 2",self.stats_iteration[1]
        return pid_stats #KEY==> PID, Value==>["SeviceName","port", "CPU%"]

class Memory:
    def __init__(self,pids):
        self.pids=pids
        #self.pagesize = os.sysconf("SC_PAGE_SIZE") / 1024 #KiB
    
    def getMemory(self,total_mem):
        pid_mem_stats=dict()
        try:
            for pids,value in self.pids.items():
                if os.path.exists("/proc/{}/status".format(pids)):
                    with open("/proc/{}/status".format(pids),'r') as f:
                        pid_mem=float(f.readlines()[15].split()[1])
                        pid_mem_stats.setdefault(pids,[value[0],value[1],round((pid_mem/total_mem)*100,5)])
                else:
                    pid_mem_stats.setdefault(pids,[value[0],value[1],0])
            return pid_mem_stats ##KEY==> PID, Value==>["SeviceName","port", "MEM"]
        except:
            log_it("error","/proc read error. "+traceback.format_exc())
            print traceback.format_exc()
            return None
        

if __name__=='__main__':
    #utils.drop_privileges()
    with open("/proc/meminfo") as f:
        total_mem=float(f.readlines()[0].split()[1]) #kB
    #print "TOTAL MEM",total_mem
    p=PIDs(service_list)
    p.daemon=True
    p.start()
    time.sleep(1) # To make sure PIDs re ready from the thread
    while True:
        pids=p.getPIDs()
        if pids:
            cpu=CPU(pids)
            mem=Memory(pids)
            proc_mem=mem.getMemory(total_mem)
            proc_cpu=cpu.getCPU()
            ts=int(time.time())
            if proc_cpu and proc_mem:
                for (cpu_pid, cpu_list), (mem_pid, mem_list) in zip(proc_cpu.items(), proc_mem.items()):
                    print "service.cpu.util {} {} pid={} service={} port={}".format(ts,cpu_list[2],cpu_pid,cpu_list[0],cpu_list[1])
                    print "service.mem.util {} {} pid={} service={} port={}".format(ts,mem_list[2],mem_pid,mem_list[0],mem_list[1])
        else:
            log_it("info","Service PIDs not found. Services are running?")
            time.sleep(5)
        sys.stdout.flush()

  
