import os
import sys
import click

from utils import str2timestamp

try:
    from core.base_detector import Detector
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
    from core.base_detector import Detector


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
