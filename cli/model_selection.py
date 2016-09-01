import re
import os
import sys
import click
import configparser
import numpy as np

from utils import str2timestamp

try:
    from core.datadog_client import DatadogClient
    from core.changefinder.ar_1d import ModelSelection
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
    from core.datadog_client import DatadogClient
    from core.changefinder.ar_1d import ModelSelection


@click.command()
@click.option('--max_k', default=50, help='Max number of k for AR(k).')
@click.option('--start', prompt='Start', help='Datetime starting relay from.')
@click.option('--end', prompt='End', help='Datetime starting relay to.')
@click.option('--timezone', default='UTC', help='Timezone of the datetime.')
def cli(max_k, start, end, timezone):
    time_start = str2timestamp(start, timezone)
    time_end = str2timestamp(end, timezone)

    assert (time_end - time_start <= 60 * 60 * 24), 'Time range must be smaller than 24 hours'

    parser = configparser.ConfigParser()
    parser.read(os.getcwd() + '/config/datadog.ini')

    dd_section_names = [s for s in parser.sections()
                        if re.match('^datadog\..*$', s) is not None]

    dd_sections = {}
    for section_name in dd_section_names:
        dd_sections[section_name] = parser[section_name].get('query')

    dd = DatadogClient(app_key=os.environ['DD_APP_KEY'],
                       api_key=os.environ['DD_API_KEY'])

    selector = ModelSelection(max_k)

    for section_name, query in dd_sections.items():
        series = dd.get_series(time_start, time_end, query)
        x = np.array([(0.0 if s['raw_value'] is None else s['raw_value']) for s in series])

        selected_k, min_aic = selector.select(x)

        print('[%s] %s\n  k = %d (AIC = %f)' % (section_name, query, selected_k, min_aic))


if __name__ == '__main__':
    cli()
