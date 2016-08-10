from abc import ABCMeta, abstractmethod

from fluent import sender
from fluent import event

import os
import configparser

from .datadog_api_helper import DatadogAPIHelper
from .changefinder import ChangeFinder


class Detector:

    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, fluent_tag_prefix):
        sender.setup(fluent_tag_prefix)

        parser = configparser.ConfigParser()
        parser.read(os.getcwd() + '/config/datadog.ini')
        self.queries = parser['datadog'].get('queries').strip().split('\n')

        # create ChangeFinder instances for each query (metric)
        self.cfs = {}
        for query in self.queries:
            self.cfs[query] = ChangeFinder(r=0.01, k=1, smooth=10)

        self.dd = DatadogAPIHelper(app_key=os.environ['DD_APP_KEY'],
                                   api_key=os.environ['DD_API_KEY'])

    def query(self, start, end):
        for query in self.queries:
            series = self.dd.get_series(start, end, query)
            self.handle_series(query, series)

    def handle_series(self, query, series):
        for s in series:
            s['raw_value'] = 0.0 if s['raw_value'] is None else s['raw_value']
            score_outlier, score_change = self.cfs[query].update(s['raw_value'])

            record = self.get_record(s, score_outlier, score_change)
            event.Event(s['src_metric'], record)

    def get_record(self, s, score_outlier, score_change):
        return {'metric': s['src_metric'],
                'raw_value': s['raw_value'],
                'metric_outlier': 'changefinder.outlier.' + s['src_metric'],
                'score_outlier': score_outlier,
                'metric_change': 'changefinder.change.' + s['src_metric'],
                'score_change': score_change,
                'time': int(s['time'] / 1000)  # same as Ruby's unix time
                }
