#!/bin/sh

sed -i "s/\/N/\/${rerun_in_minutes}/g" /etc/cron.d/app-cron

crontab /etc/cron.d/app-cron
exec "$@"