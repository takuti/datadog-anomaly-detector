Instruction for the others
===

### 1. Login to a server

	$ ssh username@foo.com

We assume that td-agent and Norikra are already running on the instance. In order to start/stop them, use the following commands.

td-agent:

	$ sudo service td-agent start
	$ sudo service td-agent stop

Norikra:

	$ norikra start --stats=/etc/norikra/norikra.json -l /var/log/norikra -Xmx2g --daemonize
	$ norikra stop

### 2. Configure monitored Datadog queries

First, enter a directory which contains forked code and sample settings ([repository](https://github.com/takuti/datadog-anomaly-detector)).

	$ cd $HOME/datadog-anomaly-detector

We already have a config *datadog.ini* under a *config/* directory as:

	$ cat config/datadog.ini
	[general]
	pidfile_path: /var/run/changefinder.pid

	; Datadog API access interval (in sec. range)
	interval: 600

	[datadog.cpu]
	query: system.load.norm.5{chef_environment:production,chef_role:worker6-staticip} by {host}

	r: 0.02
	k: 6
	T1: 10
	T2: 5

	[datadog.queue]
	query: avg:queue.system.running{*}

	r: 0.02
	k: 6
	T1: 10
	T2: 5

You can insert a new config for a different query (metric) by creating a new **datadog.xxx** section as:

```
[datadog.add1]
query: additional.metric.1{foo}

r: 0.02
k: 6
T1: 10
T2: 5

...
```

Note that `r`, `k`, `T1` and `T2` are the parameters of our machine learning algorithm. You can set different parameters for each query if you want. In case that you do not write the parameters on the INI file, default parameters will be set. In particular, optimal `k` is chosen by a model selection logic as described in **[doc/changefinder.md#model-selection](https://github.com/takuti/datadog-anomaly-detector/blob/master/doc/changefinder.md#model-selection)**.

### 3. Run a daemon script

Check whether a daemon script (named **daemonizer.py**) is running:

	$ ps -ax | grep daemonizer.py
	12824 ?        S      0:01 python daemonizer.py start

Run the daemon script if a process does not exist:

	$ sudo ~/.pyenv/shims/python daemonizer.py start

Now, the daemon gets points from Datadog every 10 minutes (depending on `interval` parameter in the .ini file) and passes them to Fluentd.

The daemon process can be terminated by:

	$ sudo ~/.pyenv/shims/python daemonizer.py stop


### 4. Check outlier and change point scores on Datadog

For each metric, change point and outlier scores are again passed to Datadog as new metrics. 

To give an example, when you are monitoring a query for a metric **queue.system.running** as **[datadog.queue]** section in *config/datadog.ini*, you can check its outlier and change scores on Datadog by new metrics **changefinder.outlier.queue** and **changefinder.change.queue** respectively; newly created metric names correspond to the section names on the INI file.

### 5. [Detect anomalies and notify to Slack on Norikra](https://github.com/takuti/datadog-anomaly-detector/blob/master/doc/norikra.md#example-anomaly-detection-and-slack-notification-using-norikra)

