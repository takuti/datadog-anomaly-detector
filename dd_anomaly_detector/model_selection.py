import re
import os
import click
import configparser
import numpy as np
import pytz
import time
from datetime import datetime
from tzlocal import get_localzone

from datadog_api_helper import DatadogAPIHelper
from changefinder.changefinder_1d import AR_1D


def str2timestamp(s, timezone):
    date = datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=pytz.timezone('Asia/Tokyo'))

    # Datadog API requires machine's local timestamp
    local_date = date.astimezone(get_localzone())

    return int(time.mktime(local_date.timetuple()))


@click.command()
@click.option('--max_k', default=50, help='Max number of k for AR(k).')
@click.option('--start', prompt='Start', help='Datetime starting relay from.')
@click.option('--end', prompt='End', help='Datetime starting relay to.')
@click.option('--timezone', default='UTC', help='Timezone of the datetime.')
def select_model(max_k, start, end, timezone):
    parser = configparser.ConfigParser()
    parser.read(os.getcwd() + '/config/datadog.ini')

    dd_section_names = [s for s in parser.sections()
                        if re.match('^datadog\..*$', s) is not None]

    dd_sections = {}
    for section_name in dd_section_names:
        dd_sections[section_name] = parser[section_name].get('query')

    dd = DatadogAPIHelper(app_key=os.environ['DD_APP_KEY'],
                          api_key=os.environ['DD_API_KEY'])

    time_start = str2timestamp(start, timezone)
    time_end = str2timestamp(end, timezone)

    for section_name, query in dd_sections.items():
        series = dd.get_series(time_start, time_end, query)
        x = np.array([(0.0 if s['raw_value'] is None else s['raw_value']) for s in series])

        selected_k = 1
        min_aic = np.inf

        for k in range(1, min(x.size, max_k + 1)):
            ar = AR_1D(k)
            ar.estimate(x)

            # sigma could be negative/zero
            v = max(2 * np.pi * ar.sigma, 1e-100)
            aic = x.size * (np.log(v) + 1) + 2 * (k + 1)

            if aic < min_aic:
                selected_k = k
                min_aic = aic

        print('[%s] %s\n\tk = %d (AIC = %f)' % (section_name, query, selected_k, min_aic))


if __name__ == '__main__':
    res = select_model()
