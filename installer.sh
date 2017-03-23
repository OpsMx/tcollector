#!/bin/bash

echo "*********Downloading OpsMx Tcollector *********"
sudo wget -O /tmp/tcollector_opsmx.zip https://github.com/OpsMx/tcollector/archive/master.zip
sudo apt-get update && apt-get install unzip -y
sudo unzip /tmp/tcollector_opsmx.zip -d /opt/
sudo mv /opt/tcollector-master /opt/tcollector
sudo wget -O /etc/init.d/tcollector https://raw.githubusercontent.com/OpsMx/tcollector/master/tcollector
sudo rm -rf /tmp/tcollector_opsmx.zip

echo "********* Installing OpsMx Tcollector init Script **************"
sudo chmod 755 /etc/init.d/tcollector
sudo update-rc.d tcollector defaults
service tcollector start
