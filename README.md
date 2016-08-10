Datadog Anomaly Detector
===

Get Datadog metrics and pass anomaly scores to Datadog itself via Fluentd.

## Minimal Requirements

### System

- Python 3.x (2.x is not supported)
- Fluentd 0.12.x

### Python packages

- numpy
- scipy
- datadog
- fluent-logger
- python-daemon-3K

## Basic Installation and Usage

### 1. Setup Fluentd (td-agent)

Note: You can replace `td-agent` with `fluent` depending on your system environment.

Follow [Installation | Fluentd](http://docs.fluentd.org/categories/installation) and configure `/etc/td-agent/td-agent.conf` as:

```apache
<match changefinder.**>
  @type copy
  deep_copy true

  <store>
    @type record_reformer
    renew_record true
    renew_time_key time

    tag datadog.${tag}
    <record>
      metric ${metric_outlier}
      value ${score_outlier}
      host ${host}
      time ${record["time"]}
    </record>
  </store>

  <store>
    @type record_reformer
    renew_record true
    renew_time_key time

    tag datadog.${tag}
    <record>
      metric ${metric_change}
      value ${score_change}
      host ${host}
      time ${record["time"]}
    </record>
  </store>
</match>

<match datadog.changefinder.**>
  @type dd
  dd_api_key YOUR_API_KEY
</match>
```

Since the configuration depends on [fluent-plugin-dd](https://github.com/winebarrel/fluent-plugin-dd) and [fluent-plugin-record-reformer](https://github.com/sonots/fluent-plugin-record-reformer), you need to install the plugins via `td-agent-gem`.

Finally, restart td-agent: `$ sudo service restart td-agent`.

### 2. Configure your detector

Create `config/datadog.ini` as demonstrated in `config/example.ini`.

### 3. Start a detector daemon

In order to get Datadog metrics, we need to first set API and APP keys as environmental variables `DD_APP_KEY` and `DD_API_KEY`.

Now, we are ready to start a detector daemon as:

```
$ python cf_daemon.py start
```

For the `.pid` file specified in `config/datadog.ini`, please make sure if the directories exist correctly and you have write permission for the path.

You can stop the daemon as follows.

```
$ python cf_daemon.py stop
```

## Norikra (CEP Engine) Integration

For further analysis of the anomaly scores, we can integrate the detector with CEP engines. Here, we especially focus on [Norikra](https://norikra.github.io/). 

Our scores can be easily connected to Norikra by using [fluent-plugin-norikra](https://github.com/norikra/fluent-plugin-norikra). Extending the above Fluentd config file as:

```apache
<match changefinder.**>
  @type copy
  deep_copy true

  <store>
    @type norikra
    norikra localhost:26571
    buffer_queue_limit 1
    retry_limit 0
    remove_tag_prefix changefinder
    target_map_tag true
  </store>

  <store>
    @type record_reformer
    renew_record true
    renew_time_key time

    tag datadog.${tag}
    <record>
      metric ${metric_outlier}
      value ${score_outlier}
      host ${host}
      time ${record["time"]}
    </record>
  </store>

  <store>
    @type record_reformer
    renew_record true
    renew_time_key time

    tag datadog.${tag}
    <record>
      metric ${metric_change}
      value ${score_change}
      host ${host}
      time ${record["time"]}
    </record>
  </store>
</match>
```

allows you to pass the scores both to Norikra and Datadog.

### Example: Anomaly detection and slack notification using Norikra

If you added the above Norikra configuration to the Fluentd `.conf` file, anomaly detection can be easily implemented by adding some Norikra queries.

First of all, let us merge the different metric streams to single aggregated stream by using Norikra's **LOOPBACK** feature. When we are monitoring two metrics *system.cpu.idle* and *system.disk.free*, Norikra will have two corresponding targets *system_cpu_idle* and *system_disk_free*. So, creating following queries with a group name **LOOPBACK(aggregated_metric)** enables us to aggregates the targets into a new target *aggregated_metric*:

```sql
SELECT metric, raw_value, score_outlier, score_change, time
FROM system_cpu_idle.win:time_batch(10 sec, 0L)
```

```sql
SELECT metric, raw_value, score_outlier, score_change, time
FROM system_disk_free.win:time_batch(10 sec, 0L)
```

The SQL-like syntax is called ***EPL*** (see section 5 to 14 of [Esper v5.2 Reference](http://www.espertech.com/esper/release-5.2.0/esper-reference/html/index.html)). In this case, Norikra runs the aggregation every 10 seconds as configured `.win:time_batch(10 sec)`.

Next, additional query which detects anomalies can be registered as:

```sql
SELECT a.metric AS metric,
       MAX(a.raw_value) AS raw,
       MAX(a.score_change) AS change,
       MAX(a.score_outlier) AS outlier
FROM pattern [
  every a=aggregated_metric((metric='system.cpu.idle' and score_change > 15.0) or
                            (metric='system.disk.free' and raw_value < 1000000000))
  ].win:ext_timed_batch(a.time * 1000, 1 min, 0L)
GROUP BY a.metric
HAVING count(a.metric) != 0
```

This query detects the events (i.e. anomalies) iff at least one point in a window satisfies a condition that a `raw_value` field in a `system_disk_free` target is less than 1000000000 or a `score_change` field in a `system_ipu_idle` target is greater than 15. Here, the query obtains maximum raw value, change score and outlier score for each metric per window, 

Here, window size is given for a "time" field of the record, and this field is Datadog's original timestamp (not Fluentd/Norikra's timestamp). It should be noted that `a.time * 1000` (i.e. unix time in millisecond range) should be used instead of `a.time` itself. For more information about field-based windowing, see [a reference page](http://www.espertech.com/esper/release-5.2.0/esper-reference/html/epl-views.html#view-win-ext-time-batch). 

Finally, the detected events can be fetched by Fluentd:

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

(this setting assumes that your Norikra query name is "sample_anomaly")

As a result, the fetched events can be passed everywhere you want via Fluentd. To give an example, [fluent-plugin-slack](https://github.com/sowawa/fluent-plugin-slack) enables us to notify anomalies on Slack. Sample configuration is:

```apache
<match norikra.query.**>
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

## Algorithm: ChangeFinder

The detector currently uses a well-known anomaly detection framework **ChangeFinder**. Implementation of the algorithm is based on: [aihara/changefinder](https://bitbucket.org/aihara/changefinder).

Our implementation only supports 1D inputs for now.

### References

- [SDAR algorithm](https://www.computer.org/cms/dl/trans/tk/2006/04/extras/k0482s.pdf)
- Solving the Yule-Walker equation
	- [Analytically solve the linear systems](http://mpastell.com/pweave/_downloads/AR_yw.html)
	- [Efficient recursive algorithm](http://www.leif.org/EOS/vonSt0521012309.pdf) (p. 217) 
- Other implementations
	- [fluentd plugin](https://github.com/muddydixon/fluent-plugin-anomalydetect/blob/master/lib/fluent/plugin/out_anomalydetect.rb)
	- [Java implementation](https://github.com/acromusashi/acromusashi-stream-ml/blob/master/src/main/java/acromusashi/stream/ml/anomaly/cf/ChangeFinder.java)
- Time series samples
	- [Twitter](https://blog.twitter.com/2015/introducing-practical-and-robust-anomaly-detection-in-a-time-series)
	- [Synthetic data](http://cl-www.msi.co.jp/reports/changefinder.html) (in Japanese)

## License

MIT
