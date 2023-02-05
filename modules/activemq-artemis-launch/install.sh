#!/bin/sh
set -e

SCRIPT_DIR=$(dirname $0)
ADDED_DIR=${SCRIPT_DIR}/added
SOURCES_DIR="/tmp/artifacts"
DEST=$AMQ_HOME

mkdir -p ${DEST}
mkdir -p ${DEST}/conf/

if ! ls $AMQ_HOME/lib/artemis-prometheus-metrics-plugin*.jar; then
  curl -L --output "$AMQ_HOME/lib/artemis-prometheus-metrics-plugin-2.0.0.jar" https://github.com/rh-messaging/artemis-prometheus-metrics-plugin/releases/download/v2.0.0/artemis-prometheus-metrics-plugin-2.0.0.jar
fi

if ! ls $AMQ_HOME/web/metrics.war; then
  curl -L --output "$AMQ_HOME/web/metrics.war" https://github.com/rh-messaging/artemis-prometheus-metrics-plugin/releases/download/v2.0.0/artemis-prometheus-metrics-plugin-servlet-2.0.0.war
fi

cp -p ${SOURCES_DIR}/netty-tcnative*.jar \
  ${DEST}/lib

cp -p $ADDED_DIR/jgroups-ping.xml \
  ${DEST}/conf/

cp $ADDED_DIR/launch.sh \
  ${ADDED_DIR}/readinessProbe.sh \
  ${ADDED_DIR}/drain.sh \
  $AMQ_HOME/bin

chmod 0755 $AMQ_HOME/bin/launch.sh
chmod 0755 $AMQ_HOME/bin/readinessProbe.sh
chmod 0755 $AMQ_HOME/bin/drain.sh
