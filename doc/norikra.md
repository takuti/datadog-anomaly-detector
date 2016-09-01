Norikra (CEP Engine) Integration
===

For further analysis of the anomaly scores, we can integrate the detector with CEP engines. Here, we especially focus on [Norikra](https://norikra.github.io/). 

Our scores can be easily connected to Norikra by using [fluent-plugin-norikra](https://github.com/norikra/fluent-plugin-norikra). Extending the Fluentd config file as follows allows you to pass the scores both to Norikra and Datadog.

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

## Example: Anomaly detection and Slack notification using Norikra

If you added the above Norikra configuration to the Fluentd `.conf` file, anomaly detection can be easily implemented by adding some Norikra queries.

### 1. Add Norikra aggregation queries for the targets

The records are streamed to Norikra by Fluentd, and Norikra targets will be automatically created with a corresponding name to each configured **[datadog.xxx]** sections in the INI file. For instance, a target **queue_system_running** is created for a configuration **[datadog.queue.system.running]** (a dot `.` is replaced with an underscore `_`).

On Norikra, all streams need to be aggregated into an **aggregated_metric** target to set a filter with complex conditions (e.g. AND, OR, and "less than"). So, you must add a LOOPBACK query for each target.

For the **queue_system_running** target, please add the following query with a group name **LOOPBACK(aggregated_metric)**.

```sql
SELECT metric, raw_value, score_outlier, score_change, time
FROM queue_system_running.win:time_batch(10 sec)
```

The SQL-like syntax is called ***EPL*** (see section 5 to 14 of [Esper v5.2 Reference](http://www.espertech.com/esper/release-5.2.0/esper-reference/html/index.html)). In this case, Norikra runs the aggregation every 10 seconds as configured `.win:time_batch(10 sec)`.

### 2. Add a filtering query

For the aggregated metric, we define a (complex) filtering query like:

```sql
SELECT dateformat(MAX(a.time) * 1000, 'yyyy-MM-dd HH:mm z', 'UTC') AS max_time, 
			 (MAX(a.time) + 1800) AS end_ts,
       dateformat(MIN(a.time) * 1000, 'yyyy-MM-dd HH:mm z', 'UTC') AS min_time,
			 (MIN(a.time) - 1800) AS start_ts,
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

This query detects the events (i.e. anomalies) iff at least one point in a window satisfies a condition that a raw value of a metric `system.disk.free` is less than 1000000000 or a change score of a `system.cpu.idle` metric is greater than 15. Here, the query obtains maximum raw value, change score and outlier score for each metric per window, 

In the above case, window size is given for a "time" field of the record, and this field has Datadog's original timestamp (not Fluentd/Norikra's local timestamp). It should be noted that `a.time * 1000` (i.e. unix time in millisecond range) should be used instead of `a.time` itself. For more information about field-based windowing, see [a reference page](http://www.espertech.com/esper/release-5.2.0/esper-reference/html/epl-views.html#view-win-ext-time-batch). 

In order to get date-time information of the detected anomalies for each window, the query uses [norikra-udf-dateformat](https://github.com/takuti/norikra-udf-dateformat) for both maximum and minimum values of the `time` filed. Moreover, the query gets `start_ts` and `ent_ts` which are 30 minutes before and after timestamps. The timestamps are used to take snapshots later.

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

If you test your queries and notification settings, you can use a replay script at `$HOME/datadog-anomaly-detector/cli/replay.py`. You can run the script with command-line options as:

	$ python cli/replay.py --start='2016-08-10 13:30' --end='2016-08-10 13:45'

Importantly, timezone for `start` and `end` options is UTC by default. For JST, you need to add an option `--timezone='Asia/Tokyo'`.

For all queries you wrote in the `config/datadog.ini` file, this script gets the metric values in a period from `start` to `end` (less than 24 hours). Following to the script, Fluentd and Norikra behaves very similar to what the daemon does, but Norikra target names have a prefix **replay_**.

Slack notification settings are written in `<match norikra.query.replay.**>` section in `/etc/td-agent/td-agent.conf` as follows.

```apache
<source>
  type norikra
  norikra localhost:26571
  <fetch>
    method event
    target sample_replay
    tag query_name
    tag_prefix norikra.query.replay
    interval 10s
  </fetch>
</source>

<match norikra.query.replay**>
  @type slack
  webhook_url https://hooks.slack.com/services/XXX/XXX/XXX
  channel anomaly-alert
  username "Mr. ChangeFinder (replay)"
  icon_emoji :innocent:
  flush_interval 10s
  message_keys min_time,max_time,metric,raw,change,outlier
  message ":clock1: [%s, %s]\n:house: %s\n:chart_with_upwards_trend: Max Raw %s, Max Change %s, Max Outlier %s"
</match>
```

Note that you must care about [Datadog's API rate limit](https://help.datadoghq.com/hc/en-us/articles/205060139-API-rate-limit). Replaying many times in a short period leads reaching the limit, and it also kills a running daemon.

### Optional: Slack notification with snapshots

Extending [fluent-plugin-slack (v0.6.4)](https://github.com/sowawa/fluent-plugin-slack/tree/v0.6.4) enables you to insert snapshot URLs into Slack notification messages.

First, please clone the plugin repository and apply a patch **[fluent-plugin-slack-with-dd.patch](https://github.com/takuti/datadog-anomaly-detector/blob/master/fluent-plugin-slack-with-dd.patch)** as:

	$ git am --signoff < /path/to/fluent-plugin-slack-with-dd.patch

Now, you have modified version of `fluent-plugin-slack-0.6.4/lib/fluent/plugin/out_slack.rb` in the directory, and using the script instead of the original one allows you to extend the slack-related Fluentd configuration as follows.

```apache
<match norikra.query.anomaly.**>
  @type slack

  dd_api_key YOUR_API_KEY
  dd_app_key YOUR_APP_KEY

  webhook_url https://hooks.slack.com/services/XXX/XXX/XXX
  channel anomaly-alert
  username "Mr. ChangeFinder"
  icon_emoji :ghost:
  flush_interval 10s
  message_keys min_time,max_time,metric,raw,change,outlier
  message ":clock1: [%s, %s]\n:house: %s\n:chart_with_upwards_trend: Max Raw %s, Max Change %s, Max Outlier %s"
</match>
```

(for the `norikra.query.replay` tag, you can configure similarly)
