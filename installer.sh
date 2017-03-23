#!/bin/bash

echo "*********Downloading OpsMx Tcollector *********"
sudo wget -O /tmp/tcollector_opsmx.tar https://github.com/OpsMx/tcollector/archive/master.zip
sudo tar -xvf /tmp/tcollector_opsmx.tar -C /opt/
sudo mv /opt/tcollector-master /opt/tcollector
sudo wget -O /etc/init.d/tcollector https://raw.githubusercontent.com/OpsMx/tcollector/master/tcollector
sudo rm -rf /tmp/tcollector_opsmx.tar

echo "********* Installing OpsMx Tcollector init Script **************"
sudo chmod 755 /etc/init.d/tcollector
sudo update-rc.d tcollector defaults
service tcollector start
