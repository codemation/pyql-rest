#!/bin/bash
#Usage ./restart_pyql_rest.sh <tag> <local-port> <clusterhost:port> <db-host> <db-port> <cluster> <init|join|rejoin|test> [join token]  [--no-cache]

#restart mysql db endpoint
echo "1. restarting / recreating mysql container on port "$5
./docker_db/start_db.sh mysql pyql-rest-$2 $5 $7

#ip=$(ifconfig | egrep 'netmask' | awk '{print $2}' | tail -1)
ip=$4

echo $6 | grep 'init'
if [ $? -eq 0 ]
then
    echo "1.2  create tables & saturate with test data"
    sleep 15
    # create tables & saturate with test data
    source pyql-rest-env/bin/activate
    #db['DB_HOST'], db['DB_PORT'], db['DB_NAME'], db['DB_TYPE'], db['DB_USER'], db['DB_PASSWORD']
    python test.py $ip $5 joshdb mysql josh abcd1234
fi



#./restart_pyql_rest.sh dev0.11 8091 192.168.3.33:8090 data join eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6ImQzYjIzNDcyLTcxZDQtMTFlYS1hMzIwLTg1YTA3N2E4MTY3YV9qb2luIiwiZXhwaXJhdGlvbiI6ImpvaW4iLCJjcmVhdGVUaW1lIjoxNTg1NDk2OTk4LjMwNDUyNDJ9.LrU0EvPV1Js8GFtvd86SRMzy2g9i01CyxN9zY0AdhRA
echo "2. removin existing pyql-rest containers & rebuilding image:tag pyql-rest:$1"
docker container rm pyql-rest-$2 $(docker container stop pyql-rest-$2)
docker build docker_pyql_rest/ -t joshjamison/pyql-rest:$1 $9

action=$(echo $7 | grep 'join' > /dev/null && echo -n 'join' || echo -n 'init')
env="-e PYQL_TYPE=K8S -e PYQL_VOLUME_PATH=/mnt/pyql-rest -e PYQL_PORT=$2 -e PYQL_CLUSTER_SVC=$3 -e PYQL_HOST=$ip" 
env1="-e PYQL_CLUSTER_NAME=$6 -e PYQL_CLUSTER_ACTION=$action -e PYQL_CLUSTER_TABLES=ALL -e PYQL_DEBUG=Enabled"
env2="-e PYQL_CLUSTER_JOIN_TOKEN=$7"
env3="-e DB_USER=josh -e DB_PASSWORD=abcd1234 -e DB_HOST=$ip -e DB_PORT=$5 -e DB_NAMES=joshdb -e DB_TYPE=mysql"

echo $6 | grep 'rejoin' > /dev/null 
if [ $? -eq 0 ]
then
    echo "rejoin called - will try using existing volume path"
else
    echo 'cleaning up existing volume path'
    sudo rm -rf $(pwd)/pyql-rest-$2-vol/

    # check & cleanup 
    ls $(pwd)/pyql-rest-$2-vol/ && sudo rm -rf $(pwd)/pyql-rest-$2-vol/ || echo "cleaned up existing pyql-rest volume"

    # creat new volume dir
    mkdir $(pwd)/pyql-rest-$2-vol
fi


echo "3. starting pyql rest container pyql-rest-$2"
docker container run --name pyql-rest-$2 $env $env1 $env2 $env3 -p $2:$2 -v $(pwd)/pyql-rest-$2-vol:/mnt/pyql-rest -d joshjamison/pyql-rest:$1