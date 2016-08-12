from abc import ABCMeta, abstractmethod

from fluent import sender
from fluent import event

import re
import os
import configparser

from .datadog_api_helper import DatadogAPIHelper
from .changefinder import ChangeFinder


class Detector:

    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, fluent_tag_prefix):
        sender.setup(fluent_tag_prefix)

        self.queries = []
        self.cfs = {}
        self.load_dd_config()

        self.dd = DatadogAPIHelper(app_key=os.environ['DD_APP_KEY'],
                                   api_key=os.environ['DD_API_KEY'])

    def load_dd_config(self):
        parser = configparser.ConfigParser()
        parser.read(os.getcwd() + '/config/datadog.ini')

        dd_section_names = [s for s in parser.sections()
                            if re.match('^datadog\..*$', s) is not None]

        # create ChangeFinder instances for each query (metric)
        for section_name in dd_section_names:
            s = parser[section_name]

            q = s.get('query')

            # since this method can be called multiple times,
            # only new queries (i.e. dd-related sections) are handled
            if q in self.queries:
                continue

            self.queries.append(q)

            r = float(s.get('r'))
            k = int(s.get('k'))
            T1 = int(s.get('T1'))
            T2 = int(s.get('T2'))

            self.cfs[q] = ChangeFinder(r=r, k=k, T1=T1, T2=T2)

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
        host = re.match(r'.*?host:(.*)', s['scope']).group(1) if s['scope'] != '*' else '*'

        return {'metric': s['src_metric'],
                'raw_value': s['raw_value'],
                'metric_outlier': 'changefinder.outlier.' + s['src_metric'],
                'score_outlier': score_outlier,
                'metric_change': 'changefinder.change.' + s['src_metric'],
                'score_change': score_change,
                'time': int(s['time'] / 1000),  # same as Ruby's unix time
                'host': host}
