from datadog import initialize, api

from .slack_client import SlackClient

from logging import getLogger
logger = getLogger('ChangeFinder')


class DatadogClient:

    def __init__(self, app_key, api_key, does_notify_slack=True):
        initialize(app_key=app_key, api_key=api_key)

        self.does_notify_slack = does_notify_slack

        # slack notification setting
        if does_notify_slack:
            try:
                self.slack = SlackClient()
            except RuntimeWarning:
                logger.warning('Datadog: Slack notification setting is true, but the configuration cannot be found from the .ini file.')
                self.does_notify_slack = False

    def get_series(self, start, end, query):
        """Get time series points.

        Args:
            start (int): Unix timestamp.
            end (int): Unix timestamp.
            query (string): Datadog query.

        """
        j = api.Metric.query(start=start, end=end, query=query)

        if 'errors' in j:
            msg = 'Datadog: %s' % j['errors']
            if self.does_notify_slack:
                self.slack.send_error(msg)
            raise RuntimeError(msg)
        if 'status' in j and j['status'] != 'ok':
            msg = 'Datadog: API status was NOT ok: %s' % j['status']
            if self.does_notify_slack:
                self.slack.send_error(msg)
            raise RuntimeError(msg)

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

    def __get_snapshot(self, start, end, query):
        """Get a snapshot for the given query in the period.

        Args:
            start (int): Unix timestamp.
            end (int): Unix timestamp.
            query (string): Datadog query.

        """
        j = api.Graph.create(metric_query=query, start=start, end=end)
        return j['snapshot_url']
