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

```
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
$ python detector.py start
```

For the `.pid` file specified in `config/datadog.ini`, please make sure if the directories exist correctly and you have write permission for the path.

You can stop the daemon as follows.

```
$ python detector.py stop
```

## Norikra (CEP Engine) Integration

For further analysis of the anomaly scores, we can integrate the detector with CEP engines. Here, we especially focus on [Norikra](https://norikra.github.io/). 

Our scores can be easily connected to Norikra by using [fluent-plugin-norikra](https://github.com/norikra/fluent-plugin-norikra). Extending the above Fluentd config file as:

```
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

(TODO: Add some examples here.)

## Algorithm: ChangeFinder

The detector currently uses a well-known anomaly detection framework **ChangeFinder**. Implementation of the algorithm is based on: [aihara/changefinder](https://bitbucket.org/aihara/changefinder).

Our implementation only supports 1D inputs for now.

### References

- [SDAR model](https://www.computer.org/cms/dl/trans/tk/2006/04/extras/k0482s.pdf)
- [Solving the Yule-Walker equation](http://mpastell.com/pweave/_downloads/AR_yw.html)
- [fluentd plugin](https://github.com/muddydixon/fluent-plugin-anomalydetect/blob/master/lib/fluent/plugin/out_anomalydetect.rb)
- [Java implementation](https://github.com/acromusashi/acromusashi-stream-ml/blob/master/src/main/java/acromusashi/stream/ml/anomaly/cf/ChangeFinder.java)
- [Example with synthetic data](http://cl-www.msi.co.jp/reports/changefinder.html) (in Japanese)
- [Levinson-Durbin algorithm for fast Yule-Walker solving](http://www.kumst.kyoto-u.ac.jp/kougi/time_series/Appendix1.pdf) (in Japanese)

## License

MIT
