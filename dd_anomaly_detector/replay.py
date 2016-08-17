import click

import pytz
import time
from datetime import datetime
from tzlocal import get_localzone
from base_detector import Detector


def str2timestamp(s, timezone):
    date = datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=pytz.timezone('Asia/Tokyo'))

    # Datadog API requires machine's local timestamp
    local_date = date.astimezone(get_localzone())

    return int(time.mktime(local_date.timetuple()))


@click.command()
@click.option('--start', prompt='Start', help='Datetime starting relay from.')
@click.option('--end', prompt='End', help='Datetime starting relay to.')
@click.option('--timezone', default='UTC', help='Timezone of the datetime.')
def replay(start, end, timezone):
    time_start = str2timestamp(start, timezone)
    time_end = str2timestamp(end, timezone)

    assert (time_end - time_start <= 60 * 60 * 24), 'Time range must be smaller than 24 hours'

    Detector('replay.changefinder.replay').query(time_start, time_end)


if __name__ == '__main__':
    replay()
