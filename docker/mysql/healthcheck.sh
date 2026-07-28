#!/bin/sh
# 仅检测 MySQL 是否可连接；建库由 init.sql / MYSQL_DATABASE 负责，避免健康检查超时。
set -e
export MYSQL_PWD="${MYSQL_ROOT_PASSWORD}"
mysqladmin ping -h 127.0.0.1 -uroot --silent --connect-timeout=3
