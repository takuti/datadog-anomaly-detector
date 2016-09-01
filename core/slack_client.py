import os
import slackweb
import configparser
from functools import partial

from logging import getLogger
logger = getLogger('ChangeFinder')


class SlackClient:

    def __init__(self):
        self.__load_config()

    def send_error(self, msg):
        self.slack_notifier(attachments=[{'text': msg, 'color': 'danger'}])

    def __load_config(self):
        parser = configparser.ConfigParser()
        parser.read(os.getcwd() + '/config/datadog.ini')

        if 'slack' not in parser:
            raise RuntimeWarning

        s = parser['slack']
        self.slack = slackweb.Slack(url=s.get('url'))

        channel = s.get('channel') or '#general'
        username = s.get('username') or 'Bot'
        icon_emoji = s.get('icon_emoji') or ':ghost:'

        self.slack_notifier = partial(self.slack.notify,
                                      channel=channel,
                                      username=username,
                                      icon_emoji=icon_emoji)
