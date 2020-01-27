#!/bin/bash
HOSTIP=$(cat /etc/hosts | grep $(hostname) | awk '{print $1}')
sed -i 's/PYQL_PORT/'$PYQL_PORT'/g' /etc/nginx/sites-enabled/sites-available-pyql-rest
sed -i 's/HOSTIP/'$HOSTIP'/g' /etc/nginx/sites-enabled/sites-available-pyql-rest
service nginx start
/opt/venv/bin/uwsgi --ini wsgi.ini