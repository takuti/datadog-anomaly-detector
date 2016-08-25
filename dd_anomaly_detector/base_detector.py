from abc import ABCMeta, abstractmethod

from fluent import sender
from fluent import event

import re
import os
import sys
import configparser

from datadog_api_helper import DatadogAPIHelper
from changefinder.changefinder_1d import ChangeFinder

from logging import getLogger
logger = getLogger('ChangeFinder')


class Detector:

    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, fluent_tag_prefix):
        self.ini_path = os.getcwd() + '/config/datadog.ini'

        sender.setup(fluent_tag_prefix)

        # key: config's section_name
        # value: { query: (query string), cf: (ChangeFinder instance) }
        self.dd_sections = {}
        self.load_dd_config()

        self.dd = DatadogAPIHelper(app_key=os.environ['DD_APP_KEY'],
                                   api_key=os.environ['DD_API_KEY'])

    def load_dd_config(self):
        parser = configparser.ConfigParser()
        parser.read(self.ini_path)

        dd_section_names = [s for s in parser.sections()
                            if re.match('^datadog\..*$', s) is not None]

        # delete previously existed, but now deleted sections
        for section_name in (set(self.dd_sections.keys()) - set(dd_section_names)):
            del self.dd_sections[section_name]

        # create ChangeFinder instances for each query (metric)
        for section_name in dd_section_names:
            # since this method can be called multiple times,
            # only new DD-related sections are handled
            if section_name in self.dd_sections.keys():
                continue

            self.dd_sections[section_name] = {}

            s = parser[section_name]

            q = s.get('query')
            self.dd_sections[section_name]['query'] = q

            r = float(s.get('r'))
            k = int(s.get('k'))
            T1 = int(s.get('T1'))
            T2 = int(s.get('T2'))

            try:
                self.dd_sections[section_name]['cf'] = ChangeFinder(r=r, k=k, T1=T1, T2=T2)
            except AssertionError as err:
                logger.error(err)
                sys.exit(1)

    def query(self, start, end):
        for section_name in self.dd_sections.keys():
            try:
                series = self.dd.get_series(start, end,
                                            self.dd_sections[section_name]['query'])
            except RuntimeError as err:
                logger.error(err)
                sys.exit(1)

            self.handle_series(section_name, series)

    def handle_series(self, section_name, series):
        for s in series:
            s['raw_value'] = 0.0 if s['raw_value'] is None else s['raw_value']
            try:
                score_outlier, score_change = self.dd_sections[section_name]['cf'].update(s['raw_value'])
            except AssertionError as err:
                logger.error(err)
                sys.exit(1)

            record = self.get_record(s, score_outlier, score_change)
            event.Event(re.match('^datadog\.(.*)$', section_name).group(1), record)

    def get_record(self, s, score_outlier, score_change):
        return {'metric': s['src_metric'],
                'snapshot_url': s['snapshot_url'],
                'raw_value': s['raw_value'],
                'metric_outlier': 'changefinder.outlier.' + s['src_metric'],
                'score_outlier': score_outlier,
                'metric_change': 'changefinder.change.' + s['src_metric'],
                'score_change': score_change,
                'time': int(s['time'] / 1000)}  # same as Ruby's unix time
