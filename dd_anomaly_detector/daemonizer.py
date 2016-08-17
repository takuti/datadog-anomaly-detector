import time
import configparser
from daemon import runner
from logging import getLogger, FileHandler, Formatter, INFO

from base_detector import Detector


class ChangeFinderDaemon(Detector):

    def __init__(self):
        super().__init__('changefinder')

        parser = configparser.ConfigParser()
        parser.read(self.ini_path)
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path = parser['general'].get('pidfile_path')
        self.pidfile_timeout = 5

        self.dd_api_interval = int(parser['general'].get('interval'))

    def run(self):
        logger.info('Start running a daemon')

        end = int(time.time())
        start = end - self.dd_api_interval

        while True:
            self.query(start, end)

            start = end + 1
            end = int(time.time())

            time.sleep(self.dd_api_interval)

            # incorporate new queries which were inserted during the interval
            self.load_dd_config()


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
