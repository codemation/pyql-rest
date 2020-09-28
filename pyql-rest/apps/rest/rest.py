# rest
async def run(server):
    import uuid, time, os
    from fastapi import Request
    
    log = server.log

    os.environ['HOSTNAME'] = '-'.join(os.environ['PYQL_NODE'].split('.'))
    # check pyql tables & create join jobs to join cluster
    for db in server.data:
        if db == 'pyql':
            continue
        uuid_check = await server.data['pyql'].tables['pyql'].select(
            'uuid', 
            where={'database': db}
        )
        if len(uuid_check) > 0:
            for _,v in uuid_check[0].items():
                dbuuid = str(v)
        else:
            dbuuid = str(uuid.uuid1())
            await server.data['pyql'].tables['pyql'].insert(**{
                'uuid': dbuuid,
                'database': db, 
                'lastModTime': time.time()
            })

        NODE_ID = dbuuid
        tables = []
        tables_to_join = []
        if os.environ.get('PYQL_CLUSTER_ACTION') == 'init':
            if os.environ['PYQL_CLUSTER_TABLES'].upper() == 'ALL':
                tables_to_join = [tb for tb in server.data[db].tables]
            else:
                tables_to_join = [tb for tb in os.environ['PYQL_CLUSTER_TABLES'].split(',')] #TODO - Add check for env during setup
        print(f"#REST tables_to_join {tables_to_join}")
        for tb in tables_to_join:
            if not tb in tables:
                tables.append(
                    {
                        tb: await server.get_table_config(db, tb)
                    }
                )
        print(f"#REST tables {tables}")
        if not os.environ.get('PYQL_CLUSTER_ACTION') == 'test' and not os.environ.get('PYQL_TYPE') == 'STANDALONE':
            join_cluster_job = {
                "job": f"{os.environ['HOSTNAME']}join_cluster",
                "job_type": "cluster",
                "method": "POST",
                "path": f"/cluster/{os.environ['PYQL_CLUSTER_NAME']}/join",
                "data": {
                    "name": os.environ['HOSTNAME'],
                    "path": f"{os.environ['PYQL_HOST']}:{os.environ['PYQL_PORT']}",
                    "token": server.env['PYQL_LOCAL_SERVICE_TOKEN'],
                    "database": {
                        'name': db,
                        'uuid': dbuuid
                    },
                    "tables": tables,
                    "consistency": tables_to_join # TODO - add to environ variable
                }
            }
            join_cluster_job['join_token'] = os.environ['PYQL_CLUSTER_JOIN_TOKEN']
            await server.internal_job_add(join_cluster_job)
    @server.api_route('/pyql/node')
    async def cluster_node():
        """
            returns node-id - to be used by workers instead of relying on pod ip:
        """
        log.warning(f"get node_id called {node_id}")
        return {"uuid": node_id}

    @server.api_route('/cache/reset', methods=['POST'])
    async def cluster_node_reset_cache(reason: str, request: Request):
        return await node_reset_cache(reason,  request=await server.process_request(request))

    @server.is_authenticated('local')
    @server.trace
    async def node_reset_cache(reason, **kw):
        """
            resets local db table 'cache' 
        """
        trace=kw['trace']
        trace(f"cache reset called for {reason}")
        server.reset_cache()
        return {"message": f"{nodeId} reset_cache completed"} 
    server.node_reset_cache = node_reset_cache
    #TODO - Create path for adding job to rejoin cluster if a table is discovered as added / removed