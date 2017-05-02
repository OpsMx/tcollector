#!/usr/bin/env python
'''
Author: OpsMx
Description:
1) Gets cumulative packet and byte count on open TCP ports
2) Gets active connections/connected peers
Refer: http://allanrbo.blogspot.in/2011/12/raw-sockets-with-bpf-in-python.html
Required Packages: nmap (sudo apt-get install nmap -y)
NOTE: BPF filter used.
'''
from binascii import hexlify
from ctypes import create_string_buffer, addressof
from socket import socket, AF_PACKET, SOCK_RAW, SOL_SOCKET, PACKET_OUTGOING, inet_ntoa, inet_aton
from struct import pack, unpack
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
import logging
import subprocess
import time
import threading
import re
import sys
import traceback
import os

metrics1="net.port.bytesin"
metrics2="net.port.bytesout"
metrics3="net.port.pktin"
metrics4="net.port.pktout"

metrics5="net.client.bytesin"
metrics6="net.client.bytesout"
metrics7="net.client.pktin"
metrics8="net.client.pktout"
metrics9="net.client.count"

SNIFF_INTERVAL=10
METRICS_INTERVAL=20
LOG_SIZE_LIMIT=20 #Mega Bytes Only
DEFAULT_LOG = '/var/log/sniffer.log'
PRIMARY_INTERFACE="eth0"

handler=RotatingFileHandler(DEFAULT_LOG, mode='a', maxBytes=LOG_SIZE_LIMIT*1024*1024, backupCount=0, encoding=None, delay=0)
handler.setFormatter(logging.Formatter('%(asctime)s %(name)s[%(process)d] %(levelname)s: %(message)s'))
log=logging.getLogger('OpsMx-SNIFFER')
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

def execuitcmd(cmd):
    try:
        return subprocess.check_output(cmd,shell=True)
    except:
        return None

@contextmanager
def devnull():
    new_target = open(os.devnull, "w")
    old_target, sys.stdout = sys.stdout, new_target
    try:
        yield new_target
    finally:
        sys.stdout = old_target

class OpensPorts(threading.Thread):
    '''
    Thread continuously runs for every 1 min, to look open ports in the machine
    Using nmap and fuser
    '''
    def __init__(self):
        threading.Thread.__init__(self)
        self.ports=dict()
        self.lock=threading.RLock()

    def getPorts(self):
        with self.lock:
            copy_ports=self.ports
        return copy_ports

    def run(self):
        while True:
            tmp=dict()
            cmd_output=execuitcmd("nmap -p 1-65535 localhost | tail -n+7")
            if cmd_output is not None:
                for line in cmd_output.split('\n'):
                    if line and not re.search(r'Nmap done',line) and not re.search(r'PORT',line):
                        with devnull():
                            pid_output=subprocess.check_output("fuser {}".format(line.split()[0]),shell=True)
                        if pid_output:
                            pid=int(pid_output.split()[0])
                        else:
                            pid=0
                        #print pid
                        tmp.setdefault(int(line.split("/")[0]), [line.split()[2],pid])
            else:
                log_it("critical", "'nmap' not found, please install 'sudo apt-get install nmap -y'")
                sys.exit()
            with self.lock:
                self.ports=tmp
            time.sleep(60)

class BPFSniff():
#A subset of Berkeley Packet Filter constants and macros, as defined in linux/filter.h.
    def __init__(self,interface='wlan0'): #Args--> Interface,

        self.interface=interface
        # Instruction classes
        self.BPF_LD = 0x00
        self.BPF_JMP = 0x05
        self.BPF_RET = 0x06
        # ld/ldx fields
        self.BPF_H = 0x08
        self.BPF_B = 0x10
        self.BPF_ABS = 0x20
        # alu/jmp fields
        self.BPF_JEQ = 0x10
        self.BPF_K = 0x00
        self.filters_list=list()
        self.new_open_ports=dict() #KEY==>Port, Value==>[BytesIn, BytesOut, PacketsIn, PacketsOut]
        self.lock=threading.RLock()

        self.client_packet_count=dict()#<KEY>==> Client IP, Value==>[Server PORT, PKT IN, PKT OUT, Bytes IN, Bytes OUT]

    def getSocket(self,openPorts_Object):#Args "OpensPorts" Class Object
        tmp=dict()
        filters_list=list()
        while True:
            if openPorts_Object.getPorts(): #Get at least one port
                break
            else:
                #Keep trying for ports
                time.sleep(5)

        thread_ports=openPorts_Object.getPorts()
        for port, name in thread_ports.items():
            if port in self.new_open_ports:
                tmp[port]=self.new_open_ports[port]
            else:
                tmp[port]=[name,0,0,0,0] #BytesIn, BytesOut, PacketsIn, PacketsOut

        self.new_open_ports=tmp
        log_it("info", "Ports and its Stats\n"+str(self.new_open_ports)+"\n")
        instruction_count_dst=len(self.new_open_ports)-1
        instruction_count_src=len(self.new_open_ports)*2
        #Source Port Filters
        filters_list.append(self.bpf_stmt(self.BPF_LD | self.BPF_H | self.BPF_ABS, 34))
        for ports in self.new_open_ports:
            filters_list.append(self.bpf_jump(self.BPF_JMP | self.BPF_JEQ | self.BPF_K, ports, instruction_count_src, 0))
            instruction_count_src=instruction_count_src-1

        #Destination Port Filters
        filters_list.append(self.bpf_stmt(self.BPF_LD | self.BPF_H | self.BPF_ABS, 36))
        for ports in self.new_open_ports:
            if instruction_count_dst!=0:
                filters_list.append(self.bpf_jump(self.BPF_JMP | self.BPF_JEQ | self.BPF_K, ports, instruction_count_dst, 0))
            else:
                filters_list.append(self.bpf_jump(self.BPF_JMP | self.BPF_JEQ | self.BPF_K, ports, 0, 5))
            instruction_count_dst=instruction_count_dst-1

        # Must be TCP (check protocol field at byte offset 23)
        filters_list.append(self.bpf_stmt(self.BPF_LD | self.BPF_B | self.BPF_ABS, 23))
        filters_list.append(self.bpf_jump(self.BPF_JMP | self.BPF_JEQ | self.BPF_K, 0x06, 0, 3))

        # Must be IPv4 (check ethertype field at byte offset 12)
        filters_list.append(self.bpf_stmt(self.BPF_LD | self.BPF_H | self.BPF_ABS, 12))
        filters_list.append(self.bpf_jump(self.BPF_JMP | self.BPF_JEQ | self.BPF_K, 0x0800, 0, 1))

        filters_list.append(self.bpf_stmt(self.BPF_RET | self.BPF_K, 0x0fffffff)) #pass
        filters_list.append(self.bpf_stmt(self.BPF_RET | self.BPF_K, 0))  #reject

        filters = ''.join(filters_list)
        b=create_string_buffer(filters)
        mem_addr_of_filters = addressof(b)
        fprog=pack('HL', len(filters_list), mem_addr_of_filters)
        # As defined in asm/socket.h
        SO_ATTACH_FILTER = 26
        # Create listening socket with filters
        s=socket(AF_PACKET, SOCK_RAW, 3)
        s.setsockopt(SOL_SOCKET, SO_ATTACH_FILTER, fprog)
        s.bind((self.interface, 3)) # "3" is for bidirectional traffic
        return s #Returning Socket

    def bpf_jump(self,code, k, jt, jf):
        return pack('HBBI', code, jt, jf, k)

    def bpf_stmt(self,code, k):
        return self.bpf_jump(code, k, 0, 0)

    def __parseFrame(self,raw_packet,pkt_type,len):
        try:
            ip_header_lenght=int(raw_packet[29],16)
            src_ip=inet_ntoa(pack(">L",int(raw_packet[52:60],16)))
            dst_ip=inet_ntoa(pack(">L",int(raw_packet[60:68],16)))
            offset_port=((ip_header_lenght*32)/8)+14
            port_position=(offset_port*2)
            src_port=int(raw_packet[port_position:port_position+4],16)
            dst_port=int(raw_packet[port_position+4:port_position+8],16)
            key1=dst_ip+":"+str(src_port)
            key2=src_ip+":"+str(dst_port)
            if pkt_type==PACKET_OUTGOING:
                if src_port in self.new_open_ports: #Out
                    self.new_open_ports[src_port][4]=self.new_open_ports[src_port][4]+1
                    self.new_open_ports[src_port][2]=self.new_open_ports[src_port][2]+len #Bytes
                    #<KEY>==> Client IP, Value==>[Server PORT, PKT IN, PKT OUT, Bytes IN, Bytes OUT, PID]
                    if key1 in self.client_packet_count:
                        self.client_packet_count[key1][2]=self.client_packet_count[key1][2]+1
                        self.client_packet_count[key1][4]=self.client_packet_count[key1][4]+len
                    else:
                        self.client_packet_count.setdefault(key1,[src_port,0,1,0,len,self.new_open_ports[src_port][0][1]])
            else:
                if dst_port in self.new_open_ports: #In
                    self.new_open_ports[dst_port][3]=self.new_open_ports[dst_port][3]+1
                    self.new_open_ports[dst_port][1]=self.new_open_ports[dst_port][1]+len #Bytes

                    if key2 in self.client_packet_count:
                        self.client_packet_count[key2][1]=self.client_packet_count[key2][1]+1
                        self.client_packet_count[key2][3]=self.client_packet_count[key2][3]+len
                    else:
                        self.client_packet_count.setdefault(key2,[dst_port,1,0,len,0,self.new_open_ports[dst_port][0][1]])
        except:
            log_it("debug","Please check the traceback \n"+traceback.format_exc())
            return

    def sniff(self,sock):
        epoch_end=int(time.time())+SNIFF_INTERVAL
        while True:
            data, addr = sock.recvfrom(65535)
            #print "info",'got data from',str(addr),':',str(hexlify(data))
            self.__parseFrame(hexlify(data),addr[2],len(data))
            if epoch_end<=int(time.time()):
                threading.Thread(target=sendNow(self.client_packet_count))
                log_it("info","Client Packet Count\n"+str(self.client_packet_count))
                self.client_packet_count={} #Emptying Var
                break


class PrintMetrics(threading.Thread):
    def __init__(self,bpf_Object):
        threading.Thread.__init__(self)
        self.bpf_Object=bpf_Object

    def run(self):
        while True:
            time.sleep(METRICS_INTERVAL)
            if self.bpf_Object.new_open_ports:
                ts=int(time.time())
                for ports,stats in self.bpf_Object.new_open_ports.iteritems(): #name #BytesIn, BytesOut, PacketsIn, PacketsOut
                    print "{} {} {} port={} pid={}".format(metrics1,ts,stats[1],ports,stats[0][1])
                    print "{} {} {} port={} pid={}".format(metrics1,ts,stats[2],ports,stats[0][1])
                    print "{} {} {} port={} pid={}".format(metrics1,ts,stats[3],ports,stats[0][1])
                    print "{} {} {} port={} pid={}".format(metrics1,ts,stats[4],ports,stats[0][1])
            else:
                log_it("info","No ports were found")
                
def sendNow(connections_packet_count):
    #<KEY>==> Client IP, Value==>[Server PORT, PKT IN, PKT OUT, Bytes IN, Bytes OUT, pid]
    if connections_packet_count:
        ts=int(time.time())
        print metrics9,len(connections_packet_count)
        print "{} {} {}".format(metrics9,ts,len(connections_packet_count))
        for client_ip,client_stats in connections_packet_count.items():
            ip=client_ip.split(":")[0]
            print "{} {} {} clientip={} port={} pid={}".format(metrics5,ts,client_stats[3],ip,client_stats[0],client_stats[5])
            #print metrics5,client_stats[3],"clientip="+ip,"port="+str(client_stats[0]),"pid="+str(client_stats[5])
            
            print "{} {} {} clientip={} port={} pid={}".format(metrics6,ts,client_stats[4],ip,client_stats[0],client_stats[5])
            #print metrics6,client_stats[4],"clientip="+ip,"port="+str(client_stats[0]),"pid="+str(client_stats[5])

            print "{} {} {} clientip={} port={} pid={}".format(metrics7,ts,client_stats[1],ip,client_stats[0],client_stats[5])
            #print metrics7,client_stats[1],"clientip="+ip,"port="+str(client_stats[0]),"pid="+str(client_stats[5])

            print "{} {} {} clientip={} port={} pid={}".format(metrics8,ts,client_stats[2],ip,client_stats[0],client_stats[5])
            #print metrics8,client_stats[2],"clientip="+ip,"port="+str(client_stats[0]),"pid="+str(client_stats[5])
    else:
        log_it("info","No clients were found")

if __name__=='__main__':
    pts=OpensPorts()
    pts.daemon=True
    pts.start()
    bpf=BPFSniff(PRIMARY_INTERFACE)
    mts=PrintMetrics(bpf) # Start the metrics thread. Agrument: BPFSniff Object
    mts.daemon=True
    mts.start()
    while True:
        bpf.sniff(bpf.getSocket(pts))
