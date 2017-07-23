# OpsMx tcollector
A forked repository of official [TCollector](https://github.com/OpenTSDB/tcollector)
### About tcollector
tcollector is a framework to collect data points and store them in OpenTSDB.
It allows you to write simple collectors that it'll run and monitor.  It also
handles the communication with the TSDs.

For more info, see the [TCollector Documentation](http://www.opentsdb.net/tcollector.html)

### Directory Tree
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
### The Config files
The Config files are located in `tcollector/collectors/etc/`
1. `opsmxconf.py` related to opsmx collectors configurations.(The following fields need to specify in `opsmxconf.py`)
    - `GLOBAL_COLLECTORS_INTERVAL` - Used to apply unique time interval for all collectors
    - `OVERRIDE` - Used to override script's collection interval time to `GLOBAL_COLLECTORS_INTERVAL`. i.e When `OVERRIDE` is True, `GLOBAL_COLLECTORS_INTERVAL` is applied to all collectors which means every collectors has same unique time interval period
    - `SERVICES` Dictionary - Select the servicies(specify `True`) that needs to monitor i.e. Retrives `CPU` and `MEM` of the service
    - `APACHE_CONFIG` Dictionary - Specify `username`, `password` and base url like `http://localhost`, if you wish to monitor `apache` web server
    - `MYSQL_CONFIG` Dictionary - Specify `username`, `password` ,`ip` and `port` to get `mysql` metrics. If you want to get more metrics, please set `True` for `extended` field
    - `POSTGRESS_CONFIG` Dictionary - Related to postgress DB, in order to get postgress metrics, specify `username`, `password`, `db`, `ip`, `port`
    
2. `config.py`
    - Most of the configurations is enough, but we need specify `port`(TSDB PORT),`host`(TSDB HOST). If necessary set `True` for `http` &`ssl`


### Select which collectors should run
Go to `tcollector/collectors/0/`, give execute permissions to the collectors that you want to be run.
```
For example:
chmod +x apache.py mysql.py
```

### How to download and start?
#### 1. MANUALL download and MANUALL start
Clone the repository
```
git clone https://github.com/OpsMx/tcollector.git
```
You should specify `host` and `port` in `tcollecor/collectors/etc/config.py` and go to `tcollector`directory(root of the tcollectors) run
```
python tcollector.py
```
If you did not specify `host` and `port` in `tcollecor/collectors/etc/config.py`, you can specify `host` and `port` as command line argument
```
python tcollector.py -H <HOST IP> -p <PORT>
```

#### 2. Download and install as init script
In this step, `host` and `port` are already configured, but you need to select which scripts should run by `chmod +x <collector name>` in `tcollector/collectors/0/`
```
sudo wget -O installer.py https://raw.githubusercontent.com/OpsMx/tcollector/master/installer.sh && chmod +x installer.py && sh installer.py

service tcollector start
service tcollector stop
service tcollector restart
service tcollector uninstall
```
### tcollector in Docker
`docker pull opsmx11/tcollector`

`docker run --net=host --privileged --volume=/var/lib/docker/:/var/lib/docker:ro --volume=/:/opsmx/  --volume=/sys/fs/cgroup/:/sys/fs/cgroup/:ro -it --name=opsmx-collector -d  opsmx11/tcollector`

