from datadog import initialize, api


class DatadogAPIHelper:

    def __init__(self, app_key, api_key):
        initialize(app_key=app_key, api_key=api_key)

    def get_series(self, start, end, query):
        """Get time series points.

        Args:
            start (int): Unix timestamp.
            end (int): Unix timestamp.
            query (string): Datadog query.

        """
        j = api.Metric.query(start=start, end=end, query=query)

        if 'errors' in j:
            raise RuntimeError('Datadog: %s' % j['errors'])
        if 'status' in j and j['status'] != 'ok':
            raise RuntimeError('Datadog: API status was NOT ok: %s' % j['status'])

        series = []

        for d in j['series']:
            # p = [ timestamp, value ]
            series += [{'src_metric': d['metric'],
                        'scope': d['scope'],
                        'time': int(p[0]),
                        'raw_value': p[1]
                        } for p in d['pointlist']]

        return sorted(series, key=lambda d: d['time'])

    def post_metric(self, metric, points, host):
        """Post the given points to a specified metric with host information.

        Args:
            metric (str): Destination metric name.
            points (one of belows):
                p value
                (p time, p value)
                [(p_1 time, p_1 value), ..., (p_n time, p_n value)]
            host: Metric source.

        """
        api.Metric.send(metric=metric, points=points, host=host)
