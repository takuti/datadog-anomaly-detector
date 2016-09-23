#!/bin/bash
### BEGIN INIT INFO
# Provides: changefinder
# Required-Start:
# Should-Start:
# Required-Stop:
# Should-Stop:
# Default-Start:  3 5
# Default-Stop:   0 1 2 6
# Short-Description: ChangeFinder daemon process
# Description:    Runs up the test daemon process
### END INIT INFO

CF_INIFILE_PATH=/etc/changefinder/datadog.ini
CF_PIDFILE_PATH=/var/run/changefinder/changefinder.pid
CF_LOGFILE_PATH=/var/log/changefinder/changefinder.log

CF_DAEMON_ARGS="--inifile_path=${CF_INIFILE_PATH} --pidfile_path=${CF_PIDFILE_PATH} --logfile_path=${CF_LOGFILE_PATH}"

case "$1" in
  start)
    echo "Starting server"
    # Start the daemon
    ~/.pyenv/shims/python /usr/share/datadog-anomaly-detector/daemonizer.py start ${CF_DAEMON_ARGS}
    ;;
  stop)
    echo "Stopping server"
    # Stop the daemon
    ~/.pyenv/shims/python /home/ubuntu/datadog-anomaly-detector/daemonizer.py stop ${CF_DAEMON_ARGS}
    ;;
  restart)
    echo "Restarting server"
    ~/.pyenv/shims/python /home/ubuntu/datadog-anomaly-detector/daemonizer.py restart ${CF_DAEMON_ARGS}
    ;;
  *)
    # Refuse to do other stuff
    echo "Usage: /etc/init.d/changefinder {start|stop|restart}"
    exit 1
    ;;
esac

exit 0
