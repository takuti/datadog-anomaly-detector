from fluent import sender
from fluent import event

import os
import re
import time
import logging
import configparser
from daemon import runner

from datadog_api_helper import DatadogAPIHelper
from changefinder import ChangeFinder


class Detector:

    def __init__(self):
        parser = configparser.ConfigParser()
        parser.read(os.getcwd() + '/config/datadog.ini')

        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path = parser['general'].get('pidfile_path')
        self.pidfile_timeout = 5

        sender.setup('changefinder')

        self.query = parser['datadog'].get('query')

        self.cf = ChangeFinder(r=0.005, order=1, smooth=10)

        self.dd = DatadogAPIHelper(app_key=os.environ['DD_APP_KEY'],
                                   api_key=os.environ['DD_API_KEY'])

        self.window_sec = 60 * 10  # 10 min
        self.end = int(time.time())
        self.start = self.end - self.window_sec

    def run(self):
        logger.info('Start running a daemon')

        while True:
            series = self.dd.get_series(self.start, self.end, self.query)

            for d in series:
                record = {}

                record['raw_value'] = 0.0 if d['raw_value'] is None else d['raw_value']

                # threshold will be around 15
                s_outlier, s_change = self.cf.update(record['raw_value'])

                record['metric_outlier'] = 'changefinder.outlier.' + d['src_metric']
                record['score_outlier'] = s_outlier

                record['metric_change'] = 'changefinder.change.' + d['src_metric']
                record['score_change'] = s_change

                # nb. of digits must be equal to Ruby's unix time
                record['time'] = int(d['time'] / 1000)

                host = re.match(r'.*?host:(.*)', d['scope']).group(1)
                record['host'] = host

                event.Event(d['src_metric'], record)

            self.start = self.end + 1
            self.end = int(time.time())

            time.sleep(self.window_sec)


if __name__ == '__main__':
    logger = logging.getLogger('DaemonLog')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(os.getcwd() + '/changefinder.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    daemon_runner = runner.DaemonRunner(Detector())
    daemon_runner.daemon_context.files_preserve = [handler.stream]
    daemon_runner.do_action()
