import click

import pytz
from datetime import datetime
from base_detector import Detector


@click.command()
@click.option('--start', prompt='Start', help='Datetime starting relay from.')
@click.option('--end', prompt='End', help='Datetime starting relay to.')
@click.option('--timezone', default='Asia/Tokyo', help='Timezone of the datetime.')
def replay(start, end, timezone):
    time_start = int(datetime.strptime(start, '%Y-%m-%d %H:%M').replace(tzinfo=pytz.timezone(timezone)).timestamp())
    time_end = int(datetime.strptime(end, '%Y-%m-%d %H:%M').replace(tzinfo=pytz.timezone(timezone)).timestamp())

    assert (time_end - time_start <= 60 * 60 * 24), 'Time range must be smaller than 24 hours'

    Detector('replay.changefinder.replay').query(time_start, time_end)


if __name__ == '__main__':
    replay()
