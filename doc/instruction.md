Instruction for the others
===

### 1. Login to a server

	$ ssh username@foo.com

We assume that td-agent and Norikra are already running on the instance.

### 2. Configure monitored Datadog queries

First, enter a directory which contains forked code and sample settings ([repository](https://github.com/takuti/datadog-anomaly-detector)).

	$ cd datadog-anomaly-detector

We already have a config *datadog.ini* under a *config/* directory as:

	$ cat config/datadog.ini
	[general]
	pidfile_path: /var/run/changefinder.pid

	; Datadog API access interval (in sec. range)
	interval: 600

	[datadog.cpu]
	query: system.load.norm.5{chef_environment:production,chef_role:worker6-staticip} by {host}

	; ChangeFinder hyperparameters
	r: 0.02
	k: 7
	T1: 10
	T2: 5

	[datadog.queue]
	query: avg:queue.system.running{*}

	r: 0.02
	k: 7
	T1: 10
	T2: 5

You can insert a new config for a different query (metric) by creating a new **datadog.xxx** section as:

```
[datadog.add1]
query: additional.metric.1{foo}

r: 0.02
k: 7
T1: 10
T2: 5

...
```

Note that `r`, `k`, `T1` and `T2` are the parameters of our machine learning algorithm. You can set different parameters for each query if you want. In particular, you can use **dd_anomaly_detector/model_selection.py** to find optimal `k`. For more detail, see **doc/changefinder.md#model-selection**.

### 3. Run a daemon script

Check whether a daemon script (named **daemonizer.py**) is running, and stop it if you find a process:

	$ ps -ax | grep daemonizer.py
	12824 ?        S      0:01 python dd_anomaly_detector/daemonizer.py start

	$ sudo ~/.pyenv/shims/python dd_anomaly_detector/daemonizer.py stop

Run the daemon script:

	$ sudo nohup ~/.pyenv/shims/python dd_anomaly_detector/daemonizer.py start > out.log 2> error.log

Now, the daemon gets points from Datadog every 10 minutes and passes them to Fluentd.

### 4. Check outlier and change point scores on Datadog

For each metric, change point and outlier scores are again passed to Datadog as new metrics. 

To give an example, when you inserted a query for a metric **additional.metric.1** into *config/datadog.ini*, you can check its outlier and change scores on Datadog by new metrics **changefinder.outlier.additional.metric.1** and **changefinder.change.additional.metric.1** respectively.

### 5. Add Norikra aggregation queries

By Fluentd, the records are streamed to Norikra. For each metric, a Norikra target will be created with the same name. For instance, a target **additional_metric_1** is created for a metric **additional.metric.1** (a period `.` is replaced with an underscore `_`).

On Norikra, all metric streams need to be aggregated into an **aggregated_metric** target. So, you must add a LOOPBACK query for each metric you specified in the *config/datadog.ini*.

For the **additional.metric.1** metric, please add the following query with a group name **LOOPBACK(aggregated_metric)**.

```sql
SELECT metric, raw_value, score_outlier, score_change, time
FROM additional_metric_1.win:time_batch(10 sec)
```

The SQL-like syntax is called ***EPL*** (see section 5 to 14 of [Esper v5.2 Reference](http://www.espertech.com/esper/release-5.2.0/esper-reference/html/index.html)). In this case, Norikra runs the aggregation every 10 seconds as configured `.win:time_batch(10 sec)`.

### 6. Add a filtering query for anomaly detection and Slack notification

For the aggregated metric, we finally define a filtering query like:

```sql
SELECT a.metric AS metric,
       MAX(a.raw_value) AS raw,
       MAX(a.score_change) AS change,
       MAX(a.score_outlier) AS outlier
FROM pattern [
  every a=aggregated_metric((metric='system.cpu.idle' and score_change > 15.0) or
                            (metric='system.disk.free' and raw_value < 1000000000))
  ].win:ext_timed_batch(a.time * 1000, 1 min)
GROUP BY a.metric
HAVING count(a.metric) != 0
```

This query detects the events (i.e. anomalies) iff at least one point in a window satisfies a condition that a `raw_value` field in a `system_disk_free` target is less than 1000000000 or a `score_change` field in a `system_ipu_idle` target is greater than 15. Here, the query obtains maximum raw value, change score and outlier score for each metric per window, 

Here, window size is given for a "time" field of the record, and this field is Datadog's original timestamp (not Fluentd/Norikra's timestamp). It should be noted that `a.time * 1000` (i.e. unix time in millisecond range) should be used instead of `a.time` itself. For more information about field-based windowing, see [a reference page](http://www.espertech.com/esper/release-5.2.0/esper-reference/html/epl-views.html#view-win-ext-time-batch). 

The detected events can be fetched by Fluentd:


```apache
<source>
  type norikra
  norikra localhost:26571
  <fetch>
    method event
    target sample_anomaly
    tag query_name
    tag_prefix norikra.query
    interval 10s
  </fetch>
</source>
```

(this setting assumes that your Norikra filtering query name is "sample_anomaly")

As a result, the fetched events can be passed everywhere you want via Fluentd. To give an example, [fluent-plugin-slack](https://github.com/sowawa/fluent-plugin-slack) enables us to notify anomalies on Slack. Sample configuration is:

```apache
<match norikra.query.anomaly.**>
  @type slack
  webhook_url https://hooks.slack.com/services/XXX/XXX/XXX
  channel anomaly-alert
  username "Mr. ChangeFinder"
  icon_emoji :ghost:
  flush_interval 10s
  message_keys metric,raw,change,outlier
  message ":house: %s\n:chart_with_upwards_trend: Max Raw %s, Max Change %s, Max Outlier %s"
</match>
```

You can modifily the settings on `/etc/td-agent/td-agent.conf`.

### 7. Replay with the previous data points

If you test your queries and notification settings, you can use a replay script at `$HOME/datadog-anomaly-detector/dd_anomaly_detecto/replay.py`. Let us again go back to the directory:

	$ cd $HOME/datadog-anomaly-detector

You can run the script with command-line options as:

	$ python dd_anomaly_detector/replay.py --start='2016-08-10 13:30' --end='2016-08-10 13:45'

For all metrics you wrote in the `config/datadog.ini` file, this script gets the metric values in a period from `start` to `end` (less than 24 hours). Following to the script, Fluentd and Norikra behaves very similar to what the daemon did, but Norikra target names have a new prefix **replay_**.

Slack notification settings are written in `<match norikra.query.replay.**>` section in `/etc/td-agent/td-agent.conf`.
