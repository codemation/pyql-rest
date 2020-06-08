#!/bin/bash
#usage: - ./docker_db/start_db.sh mysql pyql-rest02 3306 init|join|rejoin
docker container rm $1-$2-instance $(docker container stop $1-$2-instance)

echo $4 | grep 'rejoin' > /dev/null 
if [ $? -eq 0 ]
then
    echo "rejoin called - will try using existing volume path - "$(pwd)
else
    echo 'cleaning up existing volume path - '$(pwd)'/volume-'$2
    sudo rm -rf $(pwd)/volume-$2

    # check & cleanup 
    ls $(pwd)/volume-$2 && sudo rm -rf $(pwd)/volume-$2 || echo "cleaned up existing pyql-rest db volume"

    # creat new volume dir
    mkdir $(pwd)/volume-$2
fi

env="-e MYSQL_ROOT_PASSWORD=abcd1234 -e MYSQL_USER=josh -e MYSQL_PASSWORD=abcd1234 -e MYSQL_DATABASE=joshdb"
docker run --name $1-$2-instance -v $(pwd)/volume-$2:/var/lib/mysql $env -p $3:3306 -d joshjamison/$1