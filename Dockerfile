############################################################
# Dockerfile to build OpsMx-tcollector container image
# Based on Ubuntu
############################################################

FROM ubuntu:14.04
MAINTAINER OpsMx
RUN apt-get update && apt-get upgrade -y

################## INSTALLING PACKAGES ##################

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive \
            apt-get install -y python-software-properties \
            libmysqlclient-dev vim python-dev \
            net-tools conntrack traceroute inetutils-ping \
            tcpdump python python-pip build-essential wget sudo
RUN pip install --upgrade pip
RUN pip install MySQL-python pymongo psycopg2

################## OpsMx Tcollector ##################

RUN mkdir -p /opt/tcollector/collectors
ADD collectors /opt/tcollector/collectors
ADD tcollector /etc/init.d/tcollector
ADD tcollector.py /opt/tcollector/tcollector.py
RUN chmod -x /opt/tcollector/collectors/0/*
RUN chmod +x /opt/tcollector/collectors/0/docker.py
RUN chmod 755 /etc/init.d/tcollector
RUN update-rc.d tcollector defaults
CMD ["python","/opt/tcollector/tcollector.py"]
