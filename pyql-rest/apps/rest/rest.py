# rest
def run(server):
    import uuid, time, os
    log = server.log

    os.environ['HOSTNAME'] = '-'.join(os.environ['PYQL_NODE'].split('.'))
    # check pyql tables & create join jobs to join cluster
    for db in server.data:
        if db == 'pyql':
            continue
        uuidCheck = server.data['pyql'].tables['pyql'].select('uuid', where={'database': db})
        if len(uuidCheck) > 0:
            for _,v in uuidCheck[0].items():
                dbuuid = str(v)
        else:
            dbuuid = str(uuid.uuid1())
            server.data['pyql'].tables['pyql'].insert(**{
                'uuid': dbuuid,
                'database': db, 
                'lastModTime': time.time()
            })

        nodeId = dbuuid
        tables = []
        tableToJoin = []
        if os.environ['PYQL_CLUSTER_ACTION'] == 'init':
            if os.environ['PYQL_CLUSTER_TABLES'] == 'ALL':
                tableToJoin = [tb for tb in server.data[db].tables]
            else:
                tableToJoin = [tb for tb in os.environ['PYQL_CLUSTER_TABLES'].split(',')] #TODO - Add check for env during setup
        print(f"#REST tablesToJoin {tableToJoin}")
        for tb in tableToJoin:
            if not tb in tables:
                tables.append(
                    {
                        tb: server.get_table_func(db, tb)[0]
                    })
        print(f"#REST tables {tables}")
        
        joinClusterJob = {
            "job": f"{os.environ['HOSTNAME']}joinCluster",
            "jobType": "cluster",
            "method": "POST",
            "path": f"/cluster/{os.environ['PYQL_CLUSTER_NAME']}/join",
            "data": {
                "name": os.environ['HOSTNAME'],
                "path": f"{os.environ['PYQL_NODE']}:{os.environ['PYQL_PORT']}",
                "database": {
                    'name': db,
                    'uuid': dbuuid
                },
                "tables": tables
            }
        }
        server.internal_job_add(joinClusterJob  )
        @server.route('/pyql/node')
        def cluster_node():
            """
                returns node-id - to be used by workers instead of relying on pod ip:
            """
            log.warning(f"get nodeId called {nodeId}")
            return {"uuid": nodeId}, 200
        @server.route('/cache/reset', methods=['POST'])
        def node_reset_cache(reason=None):
            reason = request.get_json() if reason == None else reason
            log.warning(f"cache reset called for {reason}")
            server.reset_cache()
        server.node_reset_cache = node_reset_cache
        #TODO - Create path for adding job to rejoin cluster if a table is discovered as added / removed