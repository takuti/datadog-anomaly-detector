import os
import time
import configparser
from daemon import runner
from logging import getLogger, FileHandler, Formatter, INFO

from src.detector import Detector


class ChangeFinderDaemon(Detector):

    def __init__(self):
        super().__init__('changefinder')

        parser = configparser.ConfigParser()
        parser.read(os.getcwd() + '/config/datadog.ini')
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path = parser['general'].get('pidfile_path')
        self.pidfile_timeout = 5

        self.window_sec = int(parser['general'].get('window_sec'))

    def run(self):
        logger.info('Start running a daemon')

        end = int(time.time())
        start = end - self.window_sec

        while True:
            self.query(start, end)

            start = end + 1
            end = int(time.time())

            time.sleep(self.window_sec)


if __name__ == '__main__':
    logger = getLogger('DaemonLog')
    logger.setLevel(INFO)
    handler = FileHandler('/var/log/changefinder.log')
    handler.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    handler.setLevel(INFO)
    logger.addHandler(handler)

    daemon_runner = runner.DaemonRunner(ChangeFinderDaemon())
    daemon_runner.daemon_context.files_preserve = [handler.stream]
    daemon_runner.do_action()
