import sys
import argparse
import time
import configparser
from daemon import runner
from logging import getLogger, FileHandler, Formatter, INFO

from core.base_detector import Detector
from core.slack_client import SlackClient


class ChangeFinderDaemon(Detector):

    def __init__(self, inifile_path, pidfile_path):
        super().__init__('changefinder', inifile_path)

        parser = configparser.ConfigParser()
        parser.read(self.inifile_path)
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path = pidfile_path
        self.pidfile_timeout = 5

        self.dd_api_interval = int(parser['general'].get('interval'))
        self.dd_api_limit = min(int(parser['general'].get('limit')), 300)

        self.is_available_slack = True
        try:
            self.slack = SlackClient()
        except RuntimeWarning:
            logger.warning('Failed Slack notification because the configuration cannot be found from the .ini file.')
            self.is_available_slack = False

    def run(self):
        end = int(time.time())
        start = end - self.dd_api_interval

        n_api_per_hour = len(self.dd_sections) * (3600 / self.dd_api_interval)
        if n_api_per_hour > self.dd_api_limit:
            msg = 'Current configuration exceeds API rate limit. Try to reduce the number of queries or use longer interval.'

            logger.warning(msg)
            if self.is_available_slack:
                self.slack.send_warning(msg)

        while True:
            try:
                # incorporate new queries which were inserted during the interval
                self.load_dd_config()
                logger.info('Monitoring %d metrics' % len(self.dd_sections))

                self.query(start, end)

                start = end + 1
                end = int(time.time())

                time.sleep(self.dd_api_interval)
            except Exception as err:
                logger.error(err)

                msg = 'Daemon starts idling due to an exception. Back to active 1 hour later. You must resolve an issue or restart a daemon.'
                logger.warning(msg)
                if self.is_available_slack:
                    self.slack.send_warning('%s\n---\n%s' % (err, msg))

                # 1h idling
                time.sleep(3600)

                end = int(time.time())
                start = end - self.dd_api_interval


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Call a daemon runner.')

    actions = ['start', 'stop', 'restart']
    parser.add_argument('action', choices=actions, help='start | stop | restart')

    parser.add_argument('--inifile_path', help='filepath to a config file')
    parser.add_argument('--pidfile_path', help='filepath to a PID file')
    parser.add_argument('--logfile_path', help='filepath to a config file')

    args = parser.parse_args()

    if sys.argv[1] not in actions:
        print('Error: 1st argument must be one of [start, stop, restart].')
        sys.exit(1)

    logger = getLogger('ChangeFinder')
    logger.setLevel(INFO)
    handler = FileHandler(args.logfile_path)
    handler.setFormatter(Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    handler.setLevel(INFO)
    logger.addHandler(handler)

    app = ChangeFinderDaemon(args.inifile_path, args.pidfile_path)
    daemon_runner = runner.DaemonRunner(app)

    if daemon_runner.action == 'start':
        logger.info('Start running a daemon')
    elif daemon_runner.action == 'stop':
        logger.info('Stop a daemon')
    elif daemon_runner.action == 'restart':
        logger.info('Restarting a daemon')

    daemon_runner.daemon_context.files_preserve = [handler.stream]
    daemon_runner.do_action()
