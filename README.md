# OpsMx tcollector
A forked repository of official [TCollector](https://github.com/OpenTSDB/tcollector)
### About tcollector
tcollector is a framework to collect data points and store them in OpenTSDB.
It allows you to write simple collectors that it'll run and monitor.  It also
handles the communication with the TSDs.

For more info, see the [TCollector Documentation](http://www.opentsdb.net/tcollector.html)

#### Download
`sudo wget -O /tmp/opsmx_tcollector.tar <URL> && sudo tar -xvf /tmp/opsmx_tcollector.tar -C /opt/`
#### Directory Tree
```
tcolletor
|-- collectors
|   |-- 0
|   |-- 300
|   |-- 900
|   |-- etc
|   `-- lib
|-- debian
|-- eos
|   `-- collectors
|-- rpm
`-- stumbleupon
```
#### The Config files
The Config files are located in `tcollector/collectors/etc/`
1. `opsmxconf.py` related to opsmx collectors configurations.(The following fields need to specify in `opsmxconf.py`)
    - `GLOBAL_COLLECTORS_INTERVAL` - Used to apply unique time interval for all collectors
    - `OVERRIDE` - Used to override script's collection interval time to `GLOBAL_COLLECTORS_INTERVAL`. i.e When `OVERRIDE` is True, `GLOBAL_COLLECTORS_INTERVAL` is applied to all collectors which means every collectors has same unique time interval period
    - `SERVICES` Dictionary - Select the servicies(specify `True`) that needs to monitor i.e. Retrives `CPU` and `MEM` of the service
    - `APACHE_CONFIG` Dictionary - Specify `username`, `password` and base url like `http://localhost`, if you wish to monitor `apache` web server
    - `MYSQL_CONFIG` Dictionary - Specify `username`, `password` ,`ip` and `port` to get `mysql` metrics. If you want to get more metrics, please set `True` for `extended` field
    - `POSTGRESS_CONFIG` Dictionary - Related to postgress DB in order to postgress metrics, specify `username`, `password`, `db`, `ip`, `port`
    
2. `config.py`
Specify values dependes on your requrement like `port`(TSDB PORT),`host`(TSDB HOST), `http`,`ssl`. If you set `daemonize`=`True`, the tcollector will run in background daemon.
 ### How to start?
Go to `tcollector`directory
```
python tcollector.py -H <TSDB IP> -p <TSDB PORT> -D
```

[![Build Status](https://travis-ci.org/OpenTSDB/tcollector.svg?branch=master)](https://travis-ci.org/OpenTSDB/tcollector)
