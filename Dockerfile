############################################################
# Dockerfile to build OpsMx-tcollector container image
# Based on Ubuntu
############################################################

FROM ubuntu:14.04
MAINTAINER OpsMx
RUN apt-get update && apt-get upgrade -y

################## INSTALLING PACKAGES ##################

RUN apt-get update
RUN apt-get install -y openjdk-7-jre
RUN apt-get install -y openjdk-7-jdk
ENV JAVA_HOME /usr/lib/jvm/java-7-openjdk-amd64
RUN apt-get install -y python-software-properties libmysqlclient-dev vim python-dev net-tools conntrack traceroute inetutils-ping libcap* tcpdump python python-pip zlib1g zlib1g-dev build-essential wget xz-utils libcap* sudo debconf-utils kmod unzip

RUN pip install --upgrade pip
RUN pip install MySQL-python pymongo psycopg2
RUN apt-get install -y supervisor
RUN printf "[supervisord]\nnodaemon=false" > /etc/supervisor/conf.d/supervisord.conf
#RUN apt-get install -y apache2
################## OpsMx Tcollector ##################

RUN mkdir -p /opt/tcollector/collectors
ADD collectors /opt/tcollector/collectors
ADD tcollector /etc/init.d/tcollector
ADD tcollector.py /opt/tcollector/tcollector.py
RUN chmod 755 /etc/init.d/tcollector
RUN update-rc.d tcollector defaults

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
