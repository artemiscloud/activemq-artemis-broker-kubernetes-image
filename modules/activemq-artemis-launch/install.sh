#!/bin/sh
set -e

SCRIPT_DIR=$(dirname $0)
ADDED_DIR=${SCRIPT_DIR}/added
SOURCES_DIR="/tmp/artifacts"
DEST=$AMQ_HOME

mkdir -p ${DEST}
mkdir -p ${DEST}/conf/

cp -p ${SOURCES_DIR}/openshift-ping-common*.jar \
  ${SOURCES_DIR}/openshift-ping-dns*.jar \
  ${SOURCES_DIR}/netty-tcnative*.jar \
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
