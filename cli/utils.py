import pytz
import time
from datetime import datetime
from tzlocal import get_localzone


def str2timestamp(s, timezone):
    date = datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=pytz.timezone(timezone))

    # Datadog API requires machine's local timestamp
    local_date = date.astimezone(get_localzone())

    return int(time.mktime(local_date.timetuple()))
