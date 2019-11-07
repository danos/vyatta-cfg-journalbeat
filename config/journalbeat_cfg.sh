#!/usr/bin/env bash

systemctl stop journalbeat.service

mkdir -p /run/journalbeat
rm -f /etc/journalbeat.yml

python3 /opt/vyatta/sbin/journalbeat_cfg.py
ret_code=$?

if [ $ret_code == 0 ]
then
    systemctl start journalbeat.service
elif [ $ret_code == 255 ]
then
    # ret_code (script returns -1 but this underflows around to 255)
    #   = 255, script error, no config to read. Disable JB, return success
    exit 0
else
    echo "Journalbeat has been disabled; error(s) while parsing config" >&2
    exit $ret_code
fi
