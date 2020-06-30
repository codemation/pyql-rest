# pyql-rest
REST API access to database using PYQL JSON query syntax

## Requirements
- Docker 

### Gather required environment variables: 
- PYQL_HOST - hostname / ip which will be used to access this rest endpoint
- PYQL_PORT - port which this rest endpoint will listen for API requests
- DB_HOST - hostname / ip for rest endpoint to access database
- DB_PORT - database port which DB_HOST is listening for db connections
- DB_NAMES - comma separated list of databases which rest endpoint will manage
- DB_USER - user which will authenicate against DB_HOST Database - should have full access to specified database
- DB_PASSWORD - password for DB_USER
- DB_TYPE - mysql|sqlite3
Note: Using a type 'sqlite3' database only requires PYQL_HOST, DB_NAMES & DB_TYPE vars


### Standalone variables
Standalone instances require a PYQL username / password used for authenticating the API requests & administering REST endpoint 
- PYQL_USER - user which will administer pyql rest endpoint or simply access rest endpoint data 
- PYQL_PASSWORD - password for PYQL_USER
- PYQL_TYPE - default is K8s, use PYQL_TYPE=STANDALONE for standalone instances


### Quick Start - Standalone - MYSQL
- LOCAL_PATH - folder which pyql config database will be stored

        EXAMPLE: LOCAL_PATH=$(pwd)/pyql-rest-mysql

- LOCAL_PORT - local port mapped to container port - can often be the same port if not in use already

        env1="-e PYQL_HOST=192.168.1.10 -e PYQL_PORT=8090 -e PYQL_USER=pyql_admin -e PYQL_TYPE=STANDALONE -e PYQL_PASSWORD='abcd1234' -e DB_TYPE=mysql"

        env2="-e DB_HOST=192.168.1.20 -e DB_PORT=3306 -e DB_NAMES=company -e DB_USER=db_admin -e DB_PASSWORD=$(echo -n $(cat ~/.secret))"
    
        docker container run --name pyql-rest-mysql $env1 $env2 -p $LOCAL_PORT:$PYQL_PORT -v $LOCAL_PATH:/mnt/pyql-rest -d joshjamison/pyql-rest:latest


### Quick Start - Standalone - sqlite3
- LOCAL_PATH - folder which pyql config database will be stored

        EXAMPLE: LOCAL_PATH=$(pwd)/pyql-rest-mysql

- LOCAL_PORT - local port mapped to container port - can often be the same port if not in use already

        env1="-e PYQL_HOST=192.168.1.10 -e PYQL_PORT=8090 -e PYQL_TYPE=STANDALONE -e PYQL_USER=pyql_admin -e PYQL_PASSWORD='abcd1234' -e DB_TYPE=sqlite3 -e DB_NAMES=company "
    
        docker container run --name pyql-rest-mysql $env1 -p $LOCAL_PORT:$PYQL_PORT -v $LOCAL_PATH:/mnt/pyql-rest -d joshjamison/pyql-rest:latest

## PYQL Rest Setup with PYQL Cluster
A rest endpoint can be configured to join a collection of other rest endpoints (cluster), for the purposes of providing read load-balancing, data resilency, cross-database / hybrid or multi-cloud replicas. See  [pyql-cluster](https://github.com/codemation/pyql-cluster)

### PYQL Rest - Cluster Variables
- PYQL_TYPE - K8S
- PYQL_CLUSTER_SVC - HOSTNAME_OR_IP:PORT - The external host & port used to access the pyql-cluster service
- PYQL_CLUSTER_NAME - cluster to create or join
- PYQL_CLUSTER_ACTION - 'init' or 'join'
- PYQL_CLUSTER_TABLES - 'ALL' or comma separated list of tables to init / join cluster
- PYQL_CLUSTER_JOIN_TOKEN - join token generated on pyql-cluster using existing pyql-cluster user credentials See  [pyql-cluster](https://github.com/codemation/pyql-cluster)

Note: Instances may be started via docker run or within a kubernetes deployment using these variables. PYQL_HOST address must be a reachable by the pyql-cluster for an instance to correctly join / init. 

Example:

        env1="-e PYQL_HOST=192.168.1.10 -e PYQL_PORT=8090 -e PYQL_USER=pyql_admin -e PYQL_PASSWORD='abcd1234' -e DB_TYPE=mysql"

        env2="-e DB_HOST=192.168.1.20 -e DB_PORT=3306 -e DB_NAMES=company -e DB_USER=db_admin -e DB_PASSWORD=$(echo -n $(cat ~/.secret))"

        env3="-e PYQL_CLUSTER_SVC=pyql-cluster.domain.local -e PYQL_CLUSTER_NAME=data PYQL_CLUSTER_ACTION=init "

        env4="-e PYQL_CLUSTER_TABLES=ALL -e PYQL_CLUSTER_JOIN_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6ImU3MjRjODQyLWIzNDQtMTFlYS05NjgxLTYyOGNhNTQ1MTNjYyIsImV4cGlyYXRpb24iOiJqb2luIiwiY3JlYXRlVGltZSI6MTU5Mjc0Njk5Ni4xNTQ5Mjk2fQ.E-G5qPpT2hqTjp8J7tq1ZXZDE0GG6wvu_YJgmOtYLLE"

        docker container run --name pyql-rest-mysql $env1 $env2 $env3 $env4 -p $LOCAL_PORT:$PYQL_PORT -v $LOCAL_PATH:/mnt/pyql-rest -d joshjamison/pyql-rest:latest

Special Considerations:
- DOCKER ONLY - PYQL_HOST must be reachable by all pyql-cluster endpoints, if pyql cluster spans multiple subnets consider use of an external address.


K8s statefulSets & Deployments for pyql-clusters

See examples in See  [pyql-rest k8s](./k8s) and [pyql-cluster](https://github.com/codemation/pyql-cluster)

## PYQL REST - API REFERENCE

| ACTION | HTTP Verb | Path             | Request Content-Type | Request body | Response Content-Type | Example response body |
|--------|-----------|------------------|----------------------|--------------|-----------------------|-----------------------|
| CREATE Table | POST | /db/{database}/table/create | 'application/json' | {"stocks":{"columns":[{"mods":"NOT NULL AUTO_INCREMENT","name":"order_num","type":"int"},{"mods":"","name":"date","type":"str"},{"mods":"","name":"trans","type":"str"},{"mods":"","name":"symbol","type":"str"},{"mods":"DEFAULT NULL","name":"qty","type":"int"},{"mods":"DEFAULT NULL","name":"price","type":"float"},{"mods":"DEFAULT NULL","name":"afterHours","type":"bool"}],"foreignKeys":null,"primaryKey":"order_num"}} | {"message": "table created successfuly"} | 
| Get Table Config | GET | /db/{database}/table/{table}/config | - | - | 'application/json' | {"stocks":{"columns":[{"mods":"NOT NULL AUTO_INCREMENT","name":"order_num","type":"int"},{"mods":"","name":"date","type":"str"},{"mods":"","name":"trans","type":"str"},{"mods":"","name":"symbol","type":"str"},{"mods":"DEFAULT NULL","name":"qty","type":"int"},{"mods":"DEFAULT NULL","name":"price","type":"float"},{"mods":"DEFAULT NULL","name":"afterHours","type":"bool"}],"foreignKeys":null,"primaryKey":"order_num"}} | {"message": "table created successfuly"}
| Sync / Load Table | POST | /db/{database}/table/{table}/sync | 'application/json' | {"data":[{"afterHours":true,"date":"2006-01-05","order_num":2,"price":35.16,"qty":null,"symbol":null,"trans":{"condition":{"limit":"36.00","time":"EndOfTradingDay"},"type":"BUY"}},{"afterHours":true,"date":"2006-01-06","order_num":3,"price":35.12,"qty":null,"symbol":null,"trans":{"condition":{"limit":"36.00","time":"EndOfTradingDay"},"type":"BUY"}}]}
| List All Tables config | GET | /db/{database}/tables' | - | - | 'application/json' | {"tables": [{"stocks":{"columns":[{"mods":"NOT NULL AUTO_INCREMENT","name":"order_num","type":"int"},{"mods":"","name":"date","type":"str"},{"mods":"","name":"trans","type":"str"},{"mods":"","name":"symbol","type":"str"},{"mods":"DEFAULT NULL","name":"qty","type":"int"},{"mods":"DEFAULT NULL","name":"price","type":"float"},{"mods":"DEFAULT NULL","name":"afterHours","type":"bool"}],"foreignKeys":null,"primaryKey":"order_num"}} | {"message": "table created successfuly"}, {"keystore":{"columns":[{"mods":"NOT NULL","name":"env","type":"str"},{"mods":"","name":"val","type":"str"}],"foreignKeys":null,"primaryKey":"env"}}]}
| Get All Rows | GET | /db/{database}/table/{table} | - | - | 'application/json' | {"data":[{"afterHours":true,"date":"2006-01-05","order_num":2,"price":35.16,"qty":null,"symbol":null,"trans":{"condition":{"limit":"36.00","time":"EndOfTradingDay"},"type":"BUY"}},{"afterHours":true,"date":"2006-01-06","order_num":3,"price":35.12,"qty":null,"symbol":null,"trans":{"condition":{"limit":"36.00","time":"EndOfTradingDay"},"type":"BUY"}}]}
| Add row to table | POST, PUT | /db/{database}/table/{table} | 'application/json' | {"afterHours":true,"date":"2006-01-05","price":35.16,"qty":null,"symbol":null,"trans":{"condition":{"limit":"36.00","time":"EndOfTradingDay"},"type":"BUY"}} | 'application/json' | {"message": "items added"}
| Get Row with matching primary key | GET | /db/{database}/table/{table}/{key} | - | - | 'application/json' | {"data":[{"afterHours":true,"date":"2006-01-06","order_num":3,"price":35.12,"qty":null,"symbol":null,"trans":{"condition":{"limit":"36.00","time":"EndOfTradingDay"},"type":"BUY"}}]}
| Update Row with matching primary key | POST | /db/{database}/table/{table}/{key} | 'application/json' | {"price": 34:12} | 'application/json' | {"message": "OK"}
| Delete Row with matching primary key | DELETE | /db/{database}/table/{table}/{key} | - | - | 'application/json' | {"message": "OK"}
| Add row to table | POST | /db/{database}/table/{table}/insert | 'application/json' | {"afterHours":true,"date":"2006-01-05","order_num":2,"price":35.16,"qty":null,"symbol":null,"trans":{"condition":{"limit":"36.00","time":"EndOfTradingDay"},"type":"BUY"}} | 'application/json' | {"message": "items added"}
| Update Row with matching 'where' conditions | POST | /db/{database}/table/{table}/update | 'application/json' | {"set":{"price": 32:12},"where": {"type": "BUY"}} | 'application/json' | {"message": "OK"}
| Delete Row with matching 'where' conditions | POST | /db/{database}/table/{table}/delete | 'application/json' | {"where": {"afterHours": True}} | 'application/json' | {"message": "OK"}
| Select columns in rows, optionally matching 'where' conditions | POST | /db/{database}/table/{table}/select | 'application/json' | {"select":["order_num","afterHours"],"where":{"price":32.12}} | 'application/json' | {"data":[{"afterHours":true,"order_num":3}]}

## Advanced Select Usage - PYQL JSON query syntax

### Basic - Select 
| PYQL JSON | SQL |
|--------|--------|
|{"select":["*"]} | select * from {table} |
| {"select":["*"],"where":{"{column}:"value"}} | select * from {table} where {column}="value"
| {"select":["{column1}","{column2}","{column3}"],"where":{"{column1}:"value1","{column2}":"value2"}} | select {column1}, {column2}, {column3} from {table} where {column1}="value" and {column2}="value2" |
### Advanced - Select - Joins
| PYQL JSON | SQL | Info |
|--------|--------|-----|
|{"select":["*"], "join": "{table2}"} | select * from {table1} join {table2} on {table1}.fKey = {table2}.lKey | This PYQL JSON syntax assumes that {table1} has a foreignKey constraint with {table2} |
| {"select":["*"],"join":{"{table2}":{"{table1}.{column1}":"{table2}.{column2}"}} | select * from {table1} join {table2} on {table1}.{column1} = {table2}.{column2} | {table1} and {table2} do not require any foreign key constraints for this join | 

### Examples - PYQL JSON query syntax

| ACTION | HTTP Verb | Path             | Request Content-Type | Request body | SQL Query | Response Content-Type | Example response body |
|--------|-----------|------------------|----------------------|--------------|-----------|------------|-----------------------|
| Join Select with Foreign Key constraint| POST | /db/company/table/employees/select | 'application/json' | {"select":["*"],"join":"positions"} | "select * from employees join positions on employees.positionId = positions.id" | 'application/json' | {"data":[{"employees.id":1000,"employees.name":"Jane Doe","employees.positionId":100101,"positions.departmentId":1001,"positions.name":"Director"},{"employees.id":1001,"employees.name":"Dale Smith","employees.positionId":100102,"positions.departmentId":1001,"positions.name":"Manager"},{"employees.id":1002,"employees.name":"Clara Carson","employees.positionId":100102,"positions.departmentId":1001,"positions.name":"Manager"},{"employees.id":1003,"employees.name":"Jill Carson","employees.positionId":100103,"positions.departmentId":1001,"positions.name":"Rep"},{"employees.id":1004,"employees.name":"Jane Adams","employees.positionId":100103,"positions.departmentId":1001,"positions.name":"Rep"}, .. |
| Join Select w/o Foreign Key constraint | POST | /db/company/table/positions/select | 'application/json' |{"select":["*"],"join":{"departments":{"positions.departmentId":"departments.id"}},"where":{"departments.name": "HR"}} | select * from positions join departments on positoins.departmentsId = departments.id where deparments.name="HR" | 'application/json' | {"data":[{"departments.name":"HR","positions.departmentId":1001,"positions.id":100101,"positions.name":"Director"},{"departments.name":"HR","positions.departmentId":1001,"positions.id":100102,"positions.name":"Manager"},{"departments.name":"HR","positions.departmentId":1001,"positions.id":100103,"positions.name":"Rep"},{"departments.name":"HR","positions.departmentId":1001,"positions.id":100104,"positions.name":"Intern"}]}
| Multi-Join Select | POST | /db/company/table/employees/select | 'application/json' | {"select":["employees.name","positions.name","departments.name"],"join":{"positions":{"employees.positionId":"positions.id"},"departments":{"positions.departmentId":"departments.id"}},"where":{"positoins.name":"Director"}} | SELECT employees.name,positions.name,departments.name FROM employees JOIN positions ON employees.positionId = positions.id JOIN departments ON positions.departmentId = departments.id WHERE positions.name='Director' | 'application/json'| {"data":[{"departments.name":"HR","employees.name":"Jane Doe","positions.name":"Director"},{"departments.name":"Sales","employees.name":"Jane Adams","positions.name":"Director"},{"departments.name":"Support","employees.name":"Jane Doe","positions.name":"Director"},{"departments.name":"Marketing","employees.name":"Dale Wallace","positions.name":"Director"}]} |

#### Additional PYQL information
See [pyql reference](https://github.com/codemation/pyql)