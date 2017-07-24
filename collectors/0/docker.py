#!/usr/bin/python
#
# Author : OpsMx
# Description : Retrieves Docker/Kubernetes container/POD Metrics
# NOTE : Written from scratch
import os
import re
import sys
import time
import json

from collectors.etc import docker_conf
from collectors.lib import utils
from collectors.etc import opsmxconf


CONFIG = docker_conf.get_config()

if opsmxconf.OVERRIDE:
    COLLECTION_INTERVAL = opsmxconf.GLOBAL_COLLECTORS_INTERVAL
else:
    COLLECTION_INTERVAL = CONFIG['interval']

CGROUP_PATH = CONFIG["cgroup_path"]
DOCKER_DIR = CONFIG["docker_root_dir"]
PROC_DIR = CONFIG['proc']
MEMORY = {"cache": None, "rss": None,
          "mapped_file": None, "pgfault": None,
          "pgmajfault": None, "swap": None,
          "active_anon": None, "inactive_anon": None,
          "active_file": None, "inactive_file": None,
          "unevictable": None, "hierarchical_memory_limit": None}
CPU = {"user": None, "system" : None}
BLKIO = {"Read": None, "Write" : None}
container_id = re.compile(r'^[a-zA-Z0-9]{64}$')

for cpu_type in CPU.keys():
    CPU[cpu_type] = re.compile(r'.*{}.*'.format(cpu_type))
for blkio_type in BLKIO.keys():
    BLKIO[blkio_type] = re.compile(r'.*{}.*'.format(blkio_type))
for mem_type in MEMORY.keys():
    MEMORY[mem_type] = re.compile(r'.*{}.*'.format(mem_type))


def get_net_stats(pid):  # Argument is 'list'
    stats = {"rx_bytes": 0, "rx_pkt": 0,
             "tx_bytes": 0, "tx_pkt": 0}
    for ids in pid:
        dev_file = os.path.join(PROC_DIR, str(ids), "net/dev")
        if os.path.exists(dev_file):
            with open(dev_file) as f:
                for line in f.readlines():
                    if re.search(r'Inter-', line) or re.search(r'face', line) or re.search(r'lo:', line):
                        continue
                    else:
                        parts = line.split()
                        stats["rx_bytes"] = stats["rx_bytes"] + int(parts[1])
                        stats["rx_pkt"] = stats["rx_pkt"] + int(parts[2])
                        stats["tx_bytes"] = stats["tx_bytes"] + int(parts[9])
                        stats["tx_pkt"] = stats["tx_pkt"] + int(parts[10])
        return stats


class PreChecks:
    def __init__(self):
        self.config = dict()
        if os.path.exists(os.path.join(CGROUP_PATH, "blkio/kubepods")):
            self.type = "kubepods"
        elif os.path.exists(os.path.join(CGROUP_PATH, "blkio/docker")):
            self.type = "docker"
        else:
            self.type = None

    @staticmethod
    def is_files_exists():
        if os.path.exists(CGROUP_PATH) and os.path.exists(DOCKER_DIR) and os.path.exists(PROC_DIR):
            return True
        else:
            return False

    def find_dir_list(self):
        cpu_cpuacct = os.path.join(CGROUP_PATH, "cpu,cpuacct", self.type)
        cpuacct = os.path.join(CGROUP_PATH, "cpuacct", self.type)
        blkio = os.path.join(CGROUP_PATH, "blkio", self.type)
        memory = os.path.join(CGROUP_PATH, "memory", self.type)
        if os.path.exists(cpu_cpuacct):
            self.config.setdefault("cpuacct", cpu_cpuacct)
        elif os.path.exists(cpuacct):
            self.config.setdefault("cpuacct", cpuacct)
        if os.path.exists(blkio):
            self.config.setdefault("blkio", blkio)
        if os.path.exists(memory):
            self.config.setdefault("memory", memory)
        # Add 'kubepods' to paths
        if self.type == "kubepods":
            for key, item in self.config.items():
                besteffort_path = os.path.join(item, "besteffort")
                burstable_path = os.path.join(item, "burstable")
                if os.path.exists(besteffort_path):
                    self.config[key+"-besteffort"] = besteffort_path
                if os.path.exists(burstable_path):
                    self.config[key+"-burstable"] = burstable_path
                del self.config[key]


def get_info(path, ids):  # 'ids' is list type
    global container_id
    container_pids = list()
    name = None
    entity_id = None
    if ids is None:
        ids = filter(container_id.match, os.listdir(path))
        is_kube = True
    else:
        ids = [ids]
        is_kube = False
    for cid in ids:
        id_path = os.path.join(DOCKER_DIR, cid, "config.v2.json")
        if os.path.exists(id_path):
            with open(id_path) as f:
                data = json.load(f)
            pid = data["State"]["Pid"]
            if is_kube:
                try:
                    name = data["Config"]["Labels"]["io.kubernetes.pod.name"]
                    entity_id = data["Config"]["Labels"]["io.kubernetes.pod.uid"]
                except:
                    name = None
                    entity_id = None
            else:
                name = data["Name"].lstrip('/')
                entity_id = data["ID"][:12]
            container_pids.append(pid)
    return (str(entity_id), (str(name), container_pids))


def display_metrics(metric_type, ts, metric_obj, stats_file, info, docker_type):
    with open(stats_file) as f:
        lines = f.readlines()
    for sub_cat, obj in metric_obj.items():
        try:
            metric = filter(obj.match, lines)[0]
        except:
            continue
        print "docker.{}.{} {} {} id={} name={} type={}".format(metric_type, sub_cat.lower(), ts, metric.split()[-1], info[0], info[1][0], docker_type)


def main(config, docker_type):
    cid = None
    while 1:
        ts = int(time.time())
        all_pods_info = dict()
        for key, path in config.items():
            if "cpuacct" in key:
                for dirs in os.listdir(path):
                    cpu_file = os.path.join(path, dirs, "cpuacct.stat")
                    if os.path.exists(cpu_file):
                        if docker_type == "docker":
                            cid = dirs
                        info = get_info(os.path.join(path, dirs), cid)
                        all_pods_info.setdefault(info[0], info[1])
                        display_metrics("cpu", ts, CPU, cpu_file, info, docker_type)

            if "memory" in key:
                for dirs in os.listdir(path):
                    memory_file = os.path.join(path, dirs, "memory.stat")
                    if os.path.exists(memory_file):
                        if docker_type == "docker":
                            cid = dirs
                        info = get_info(os.path.join(path, dirs), cid)
                        all_pods_info.setdefault(info[0], info[1])
                        display_metrics("memory", ts, MEMORY, memory_file, info, docker_type)

            if "blkio" in key:
                for dirs in os.listdir(path):
                    blkio_file = os.path.join(path, dirs, "blkio.throttle.io_serviced")
                    if os.path.exists(blkio_file):
                        if docker_type == "docker":
                            cid = dirs
                        info = get_info(os.path.join(path, dirs), cid)
                        all_pods_info.setdefault(info[0], info[1])
                        display_metrics("blkio", ts, BLKIO, blkio_file, info, docker_type)

        for ids, info in all_pods_info.items():
            net_stat = get_net_stats(info[1])
            for name, values in net_stat.items():
                print "docker.net.{} {} {} id={} name={} type={}".format(name, ts, values, ids, info[0], docker_type)
        time.sleep(COLLECTION_INTERVAL)
        sys.stdout.flush()


if __name__ == "__main__":
    while 1:
        check = PreChecks()
        if check.type and check.is_files_exists():
            break
        print >> sys.stderr, "Not able to find pseudo files directory. 1. Check docker daemon is running? or \
                                2. Check any containers are running? 3. Check Mount directories"
        time.sleep(60)  # If Docker daemon is not running, check it for every 60 sec.
    check.find_dir_list()
    main(check.config, check.type)
