Algorithm: ChangeFinder
===

The detector currently uses a well-known anomaly detection framework **ChangeFinder**. Implementation of the algorithm is based on: [aihara/changefinder](https://bitbucket.org/aihara/changefinder).

Our implementation only supports 1D inputs for now.

## Model Selection

We can specify hyperparameters of the ChangeFinder algorithm on the config file **config/datadog.ini**. Currently, there are four hyperparamters `r`, `k`, `T1` and `T2`, and you can use **dd_anomaly_detector/model_selection.py** to find optimal `k`. Finding the best `k` value is called **model selection**.

For instance, when we have the following config file

	$ cat config/datadog.ini
	[general]
	pidfile_path: /var/run/changefinder.pid
	interval: 30

	[datadog.cpu]
	query: system.load.norm.5{chef_environment:production,chef_role:worker6-staticip} by {host}
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

**dd_anomaly_detector/model_selection.py** finds optimal `k` for each query by replaying a specific date-time range as:

	$ python dd_anomaly_detector/model_selection.py --max_k=50 --start='2016-08-10 11:45' --end='2016-08-10 12:00'
	[datadog.queue] avg:queue.system.running{*}
					k = 6 (AIC = -3424.877639)
	[datadog.cpu] system.load.norm.5{chef_environment:production,chef_role:worker6-staticip} by {host}
					k = 5 (AIC = -116909.839743)

Options are:

- `--max_k` &mdash; Max value of possible `k`.
- `--start` &mdash; Datetime replay from.
- `--end`   &mdash; Datetime replay to.

The result means that:

- According to a replay trial for the data points from `2016-08-10 11:45` to `2016-08-10 12:00`
	- for a config `[datadog.queue]`, `k = 6` is optimal in [1, 50]
	- for a config `[datadog.cpu]`, `k = 5` is optimal in [1, 50]

**AIC** is criterion to decide which `k` is the best, and smaller values indicate better `k`.

## References

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
- Model selection with AIC
	- [The AICc Criterion for Autoregressive Model Selection](http://pages.stern.nyu.edu/~churvich/TimeSeries/Handouts/AICC.pdf)
	- Japanese pages
		- http://hclab.sakura.ne.jp/stress_nervous_ar_aic.html
		- http://www.kumst.kyoto-u.ac.jp/kougi/time_series/ex1113.html

