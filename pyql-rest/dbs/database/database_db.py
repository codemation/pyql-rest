# database - type mysql
def run(server):
    import os, time
    from pyql import data
    log = server.log
    dbConnnectRetries = 10
    dbConnnectRetryDelayInSec = 5
    
    if os.environ['PYQL_CLUSTER_ACTION'] == 'test':
        os.environ['DB_USER'] = 'josh'
        os.environ['DB_PASSWORD'] = 'abcd1234'
        os.environ['DB_HOST'] = '192.168.3.33'
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_NAMES'] = 'joshdb'
        os.environ['DB_TYPE'] = 'mysql'
    
    
    env = ['DB_USER','DB_PASSWORD','DB_HOST', 'DB_PORT', 'DB_NAMES', 'DB_TYPE']

    def get_db_config():
        config=dict()
        conf = ['user','password','host','port', 'databases', 'type']
        try:
            config = {cnfVal: os.getenv(dbVal).rstrip() for dbVal,cnfVal in zip(env,conf)}
            config['logger'] = log
            if 'PYQL_DEBUG' in os.environ and os.environ['PYQL_DEBUG'] == 'Enabled':
                config['debug'] = True
        except Exception as e:
            log.error(f'Missing an environment variable, {repr(e)}')
            config= {cnfVal: os.getenv(dbVal) for dbVal,cnfVal in zip(env,conf)}
            log.error(config)
            return config, 500
        return config, 200
    def attach(config):
        database = config['database']
        tryCount = 0
        #try:
        if config['type'] == 'mysql':
            from mysql.connector import connect as connector
            if config['host'] == 'localhost':
                import socket, os
                config['host'] = socket.gethostbyname(os.environ['HOSTNAME'])
        else:
            import sqlite3.connect as connector
        while tryCount < dbConnnectRetries:
            try:
                server.data[database] = data.database(connector, **config)
                return {"message": f"db {database} attached successfully"}, 200
            except Exception as e:
                log.exception(f"enountered exception {repr(e)} during db {database} connect - sleeping {dbConnnectRetryDelayInSec} sec and retrying")
                time.sleep(dbConnnectRetryDelayInSec)
                tryCount+=1
                continue
        return {"error": log.error(f"db {database} connect failed- check parameters provided / connectivity to {config}")}, 500
        
    @server.route('/internal/db/<database>/attach')
    def attach_database(database):
        config, rc = get_db_config()
        config['database'] = database
        return attach(config)

    @server.route('/internal/dbs/attach')
    def internal_attach_databases():
        return attach_database()
    def attach_databases():
        config, rc = get_db_config()
        if rc == 500:
            return {
                "status": 500, 
                "message": "Missing environment variable(s)",
                "required": env,
                "found": config
            }, 500 
        from . import setup
        response = {'results': []}
        for database in config['databases'].split(','):
            errors = ''
            config['database'] = database
            result, rc = attach(config)
            response['results'].append({f'{database}': f'{result}'})
        setup.attach_tables(server)
        return response, 200
    server.attach_databases = attach_databases
    
    response = attach_databases()
    log.warning(response)