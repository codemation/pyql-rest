#!/bin/bash
#Usage ./restart_pyql_rest.sh <tag> <local-port> <clusterhost:port> <db-host> <db-port> <cluster> <init|join|rejoin|test> [join token]  [--no-cache]

TAG=$1
LOCAL_PORT=$2
CLUSTER_HOST_PORT=$3
DB_HOST=$4
DB_PORT=$5
CLUSTER_NAME=$6
CLUSTER_ACTION=$7
JOIN_TOKEN=$8

echo "1. restarting / recreating mysql container on port "$DB_PORT
./docker_db/start_db.sh mysql pyql-rest-$LOCAL_PORT $DB_PORT $CLUSTER_ACTION

echo $CLUSTER_ACTION | grep 'init'
if [ $? -eq 0 ]
then
    echo "1.2  create tables & saturate with test data"
    sleep 15
    # create tables & saturate with test data
    source pyql-rest-env/bin/activate
    #db['DB_HOST'], db['DB_PORT'], db['DB_NAME'], db['DB_TYPE'], db['DB_USER'], db['DB_PASSWORD']
    python test.py $DB_HOST $DB_PORT joshdb mysql josh abcd1234
fi

echo "2. removin existing pyql-rest containers & rebuilding image:tag pyql-rest:$TAG"
docker container rm pyql-rest-$2 $(docker container stop pyql-rest-$LOCAL_PORT)
docker build docker_pyql_rest/ -t joshjamison/pyql-rest:$1 $9

action=$(echo $CLUSTER_ACTION | grep 'join' > /dev/null && echo -n 'join' || echo -n 'init')
env="-e PYQL_TYPE=K8S -e PYQL_VOLUME_PATH=/mnt/pyql-rest -e PYQL_PORT=$LOCAL_PORT -e PYQL_CLUSTER_SVC=$CLUSTER_HOST_PORT -e PYQL_HOST=$DB_HOST" 
env1="-e PYQL_CLUSTER_NAME=$CLUSTER_NAME -e PYQL_CLUSTER_ACTION=$action -e PYQL_CLUSTER_TABLES=ALL -e PYQL_DEBUG=Enabled"
env2="-e PYQL_CLUSTER_JOIN_TOKEN=$JOIN_TOKEN"
env3="-e DB_USER=josh -e DB_PASSWORD=abcd1234 -e DB_HOST=$DB_HOST -e DB_PORT=$DB_PORT -e DB_NAMES=joshdb -e DB_TYPE=mysql"

echo $CLUSTER_ACTION | grep 'rejoin' > /dev/null 
if [ $? -eq 0 ]
then
    echo "rejoin called - will try using existing volume path"
else
    echo 'cleaning up existing volume path'
    sudo rm -rf $(pwd)/pyql-rest-$LOCAL_PORT-vol/

    # check & cleanup 
    ls $(pwd)/pyql-rest-$LOCAL_PORT-vol/ && sudo rm -rf $(pwd)/pyql-rest-$LOCAL_PORT-vol/ || echo "cleaned up existing pyql-rest volume"

    # creat new volume dir
    mkdir $(pwd)/pyql-rest-$LOCAL_PORT-vol
fi


echo "3. starting pyql rest container pyql-rest-$LOCAL_PORT"
docker container run --name pyql-rest-$LOCAL_PORT $env $env1 $env2 $env3 -p $LOCAL_PORT:$LOCAL_PORT -v $(pwd)/pyql-rest-$LOCAL_PORT-vol:/mnt/pyql-rest -d joshjamison/pyql-rest:$1