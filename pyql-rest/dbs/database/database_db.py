# database - type mysql
async def run(server):
    import os, time
    from fastapi.testclient import TestClient
    from fastapi.websockets import WebSocket

    log = server.log
    DB_CONNECT_MAX_RETRY = 10
    DB_CONNECT_RETRY_DELAY_IN_SEC = 5
    
    if os.environ.get('PYQL_CLUSTER_ACTION') == 'test':
        os.environ['DB_USER'] = 'josh'
        os.environ['DB_PASSWORD'] = 'abcd1234'
        os.environ['DB_HOST'] = '192.168.1.8'
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_NAMES'] = 'joshdb'
        os.environ['DB_TYPE'] = 'mysql'
    
    
    env = ['DB_USER','DB_PASSWORD','DB_HOST', 'DB_PORT', 'DB_NAMES', 'DB_TYPE']
    env = env[4:] if os.environ.get('DB_TYPE') == 'sqlite' else env

    async def get_db_config():
        config=dict()
        conf = ['user','password','host','port', 'databases', 'type']
        conf = conf[4:] if os.environ.get('DB_TYPE') == 'sqlite' else conf
        try:
            config = {cnfVal: os.getenv(db_cfg).rstrip() for db_cfg, cnfVal in zip(env,conf)}
            config['logger'] = log
            if 'PYQL_DEBUG' in os.environ and os.environ['PYQL_DEBUG'] == 'Enabled':
                config['debug'] = True
        except Exception as e:
            log.exception(f'Missing an environment variable')
            config= {cnfVal: os.getenv(dbVal) for dbVal,cnfVal in zip(env,conf)}
            log.error(config)
            return config
        return config
    async def attach(config):
        database = config['database']
        try_count = 0
        #try:
        if config['type'] == 'mysql':
            if config['host'] == 'localhost':
                import socket, os
                config['host'] = socket.gethostbyname(os.environ['HOSTNAME'])
        from aiopyql import data
        while try_count < DB_CONNECT_MAX_RETRY:
            try:
                server.data[database] = await data.Database.create(**config)
                return {"message": f"db {database} attached successfully"}
            except Exception as e:
                log.exception(f"enountered exception {repr(e)} during db {database} connect - sleeping {DB_CONNECT_RETRY_DELAY_IN_SEC} sec and retrying")
                time.sleep(DB_CONNECT_RETRY_DELAY_IN_SEC)
                try_count+=1
                continue
        return {
            "error": log.error(f"db {database} connect failed- check parameters provided / connectivity to {config}")
            }
        
    @server.api_route('/internal/db/{database}/attach')
    async def attach_database(database: str):
        config = await get_db_config()
        config['database'] = database
        return await attach(config)

    @server.api_route('/internal/dbs/attach')
    async def internal_attach_databases():
        return await attach_database()
    async def attach_databases():
        config = await get_db_config()
        log.warning(f"db config: {config}")
        missing = [e for e in config if not e in config]
        assert len(missing) == 0, f"missing environment variable(s) {missing}"

        from . import setup
        response = {'results': []}
        for database in config['databases'].split(','):
            errors = ''
            config['database'] = database
            result = await attach(config)
            response['results'].append({f'{database}': f'{result}'})
        await setup.attach_tables(server)
        return log.warning(f"attach_databases - {result}")
    server.attach_databases = attach_databases
    
    response = await attach_databases()
    log.warning(response)