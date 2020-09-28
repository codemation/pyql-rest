# rest
async def run(server):
    import uuid, time, os
    from fastapi import Request
    
    log = server.log

    os.environ['HOSTNAME'] = '-'.join(os.environ['PYQL_NODE'].split('.'))

    server.sessions = {}

    #@server.trace
    async def get_endpoint_sessions(endpoint, **kw):
        """
        pulls endpoint session if exists else creates & returns
        """
        trace = log.warning
        loop = server.event_loop if not 'loop' in kw else kw['loop']
        async def session():
            async with ClientSession(loop=loop) as client:
                trace(f"started session for endpoint {endpoint}")
                while True:
                    status = yield client
                    if status == 'finished':
                        trace(f"finished session for endpoint {endpoint}")
                        break
        if not endpoint in server.sessions:
            server.sessions[endpoint] = [{'session': session(), 'loop': loop}]
            return await server.sessions[endpoint][0]['session'].asend(None)
        for client in server.sessions[endpoint]:
            if loop == client['loop']:
                return await client['session'].asend(endpoint)
        trace("session existed but not for this event loop, creating")
        client = session()
        server.sessions[endpoint].append({'session': client, 'loop': loop})
        return await client.asend(None)

    # attaching to global server var    
    server.get_endpoint_sessions = get_endpoint_sessions

    async def cleanup_session(endpoint):
        #try:
        if endpoint in server.sessions:
            log.warning(f"removing session for endpoint {endpoint}")
            try:
                for session in server.sessions[endpoint]:
                    try:
                        await session['session'].asend('finished')
                    except StopAsyncIteration:
                        pass
                del server.sessions[endpoint]
            except Exception as e:
                log.exception("exception when cleaning up session")
        #except StopAsyncIteration:
        #    await cleanup_session(endpoint)
        #    del server.sessions[endpoint]
        #return
    async def cleanup_sessions():
        for endpoint in server.sessions:
            await cleanup_session(endpoint)
        return

    #@server.trace
    async def get_auth_http_headers(location=None, token=None, **kw):
        trace = log
        if token == None:
            auth = 'PYQL_CLUSTER_SERVICE_TOKEN' if not location == 'local' else 'PYQL_LOCAL_SERVICE_TOKEN'
            trace.warning(f"get_auth_http_headers called using location: {location} - token: {token} - {kw} auth: {auth}")
            token = kw['token'] if 'token' in kw else None
            token = await server.env[auth] if token == None else token
        headers = {
            'Accept': 'application/json', "Content-Type": "application/json",
            "authentication": f"Token {token}"}
        trace.warning(f"get_auth_http_headers {headers}")
        return headers

    #@server.trace
    async def probe(path, method='GET', data=None, timeout=5.0, auth=None, headers=None, **kw):
        trace = log
        auth = 'PYQL_CLUSTER_SERVICE_TOKEN' if not auth == 'local' else 'PYQL_LOCAL_SERVICE_TOKEN'
        headers = await get_auth_http_headers(auth, **kw) if headers == None else headers
        session, temp_session, temp_id = None, False, None
        loop = asyncio.get_running_loop() if not 'loop' in kw else kw['loop']

        if not 'session' in kw:
            temp_session, temp_id = True, str(uuid.uuid1())
            session = await get_endpoint_sessions(temp_id, loop=loop)
        else:
            session = kw['session']
            
        url = f'{path}'
        try:
            request = {
                'probe': {
                    'path': url,
                    'headers': headers,
                    'timeout': timeout
                }
            }
            if method == 'GET':
                result = await async_get_request(session, request, loop=loop) 
            else:
                request['probe']['data'] = data
                result = await async_post_request(session, request, loop=loop)
            result, status = result['probe']['content'], result['probe']['status']
        except Exception as e:
            error = f"Encountered exception when probing {path} - {repr(e)}"
            result, status = {"error": trace.error(error)}, 500
        trace.info(f"request: {request} - result: {result}")
        if temp_session:
            await cleanup_session(temp_id)
        return result, status
    server.probe = probe



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

        # creating initial session for this nodeq
        await get_endpoint_sessions(NODE_ID)
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
                    "token": await server.env['PYQL_LOCAL_SERVICE_TOKEN'],
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
        log.warning(f"get node_id called {NODE_ID}")
        return {"uuid": NODE_ID}

    @server.api_route('/cache/reset', methods=['POST'])
    async def cluster_node_reset_cache(reason: str, request: Request):
        return await node_reset_cache(reason,  request=await server.process_request(request))

    @server.is_authenticated('local')
    #@server.trace
    async def node_reset_cache(reason, **kw):
        """
            resets local db table 'cache' 
        """
        trace=log.warning
        trace(f"cache reset called for {reason}")
        await server.reset_cache()
        return {"message": f"{nodeId} reset_cache completed"} 
    server.node_reset_cache = node_reset_cache
    #TODO - Create path for adding job to rejoin cluster if a table is discovered as added / removed