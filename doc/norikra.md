Norikra (CEP Engine) Integration
===

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
      time ${record["time"]}
    </record>
  </store>
</match>
```

allows you to pass the scores both to Norikra and Datadog.

## Example: Anomaly detection and slack notification using Norikra

If you added the above Norikra configuration to the Fluentd `.conf` file, anomaly detection can be easily implemented by adding some Norikra queries.

### 1. Add Norikra aggregation queries for the targets

By Fluentd, the records are streamed to Norikra. For each metric, a Norikra target will be automatically created with the same name. For instance, a target **queue_system_running** is created for a metric **queue.system.running** (a dot `.` is replaced with an underscore `_`).

On Norikra, all metric streams need to be aggregated into an **aggregated_metric** target. So, you must add a LOOPBACK query for each metric you specified in the *config/datadog.ini*.

For the **queue.system.running** metric, please add the following query with a group name **LOOPBACK(aggregated_metric)**.

```sql
SELECT metric, raw_value, score_outlier, score_change, time
FROM queue_system_running.win:time_batch(10 sec)
```

The SQL-like syntax is called ***EPL*** (see section 5 to 14 of [Esper v5.2 Reference](http://www.espertech.com/esper/release-5.2.0/esper-reference/html/index.html)). In this case, Norikra runs the aggregation every 10 seconds as configured `.win:time_batch(10 sec)`.

### 2. Add a filtering query

For the aggregated metric, we define a filtering query like:

```sql
SELECT dateformat(MAX(a.time) * 1000, 'yyyy-MM-dd HH:mm z', 'UTC') AS max_time, 
       dateformat(MIN(a.time) * 1000, 'yyyy-MM-dd HH:mm z', 'UTC') AS min_time,
       a.metric AS metric,
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

In the above case, window size is given for a "time" field of the record, and this field is Datadog's original timestamp (not Fluentd/Norikra's timestamp). It should be noted that `a.time * 1000` (i.e. unix time in millisecond range) should be used instead of `a.time` itself. For more information about field-based windowing, see [a reference page](http://www.espertech.com/esper/release-5.2.0/esper-reference/html/epl-views.html#view-win-ext-time-batch). 

In order to get date-time information of the detected anomalies for each window, the query uses [norikra-udf-dateformat](https://github.com/takuti/norikra-udf-dateformat) for both maximum and minimum values of the `time` filed.

### 3. Set up anomaly detection and Slack notification

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
  message_keys min_time,max_time,metric,raw,change,outlier
  message ":clock1: [%s, %s]\n:house: %s\n:chart_with_upwards_trend: Max Raw %s, Max Change %s, Max Outlier %s"
</match>
```

### 4. Replay anomaly detection with the previous data points

If you test your queries and notification settings, you can use a replay script at `$HOME/datadog-anomaly-detector/cli/replay.py`. Let us again go back to the directory:

	$ cd $HOME/datadog-anomaly-detector

You can run the script with command-line options as:

	$ python cli/replay.py --start='2016-08-10 13:30' --end='2016-08-10 13:45'

Importantly, timezone for `start` and `end` options is UTC by default. For JST, you need to add an option `--timezone='Asia/Tokyo'`.

For all metrics you wrote in the `config/datadog.ini` file, this script gets the metric values in a period from `start` to `end` (less than 24 hours). Following to the script, Fluentd and Norikra behaves very similar to what the daemon did, but Norikra target names have a new prefix **replay_**.

Slack notification settings are written in `<match norikra.query.replay.**>` section in `/etc/td-agent/td-agent.conf`.
