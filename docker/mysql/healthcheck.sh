#!/bin/sh
set -e
export MYSQL_PWD="${MYSQL_ROOT_PASSWORD}"
mysqladmin ping -h 127.0.0.1 -uroot >/dev/null 2>&1
mysql -h 127.0.0.1 -uroot -e "CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE}; USE ${MYSQL_DATABASE};" >/dev/null 2>&1
