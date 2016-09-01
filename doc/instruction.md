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

### 2. [Configure monitored Datadog queries](https://github.com/takuti/datadog-anomaly-detector#2-configure-your-detector)

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

