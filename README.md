Datadog Anomaly Detector
===

Get Datadog metrics and pass anomaly scores to Datadog itself via Fluentd.

By integrating CEP engines such as [Esper](http://www.espertech.com/esper/) and [Norikra](http://norikra.github.io/), you can implement more practical applications. We introduce it in **[doc/norikra.md](https://github.com/takuti/datadog-anomaly-detector/blob/master/doc/norikra.md)**.

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

Clone this repository:

	$ git clone git@github.com:takuti/datadog-anomaly-detector.git
	$ cd datadog-anomaly-detector

Create `config/datadog.ini` as demonstrated in `config/example.ini`.

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

Note that `r`, `k`, `T1` and `T2` are the parameters of our machine learning algorithm. You can set different parameters for each query if you want. In particular, you can use **[dd_anomaly_detector/model_selection.py](https://github.com/takuti/datadog-anomaly-detector/blob/master/dd_anomaly_detector/model_selection.py)** to find optimal `k`. For more detail, see **[doc/changefinder.md#model-selection](https://github.com/takuti/datadog-anomaly-detector/blob/master/doc/changefinder.md#model-selection)**.

### 3. Start a detector daemon

In order to get Datadog metrics, we need to first set API and APP keys as environmental variables `DD_APP_KEY` and `DD_API_KEY`.

Now, we are ready to start a detector daemon as:

```
$ python dd_anomaly_detector/daemonizer.py start > out.log 2> error.log
```

For the `.pid` file specified in `config/datadog.ini`, please make sure if the directories exist correctly and you have write permission for the path.

You can stop the daemon as follows.

```
$ python dd_anomaly_detector/daemonizer.py stop
```

## License

MIT
