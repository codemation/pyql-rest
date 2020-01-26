# database - type mysql
def run(server):
    import os
    from pyql import data
    log = server.log
    
    
    """
    os.environ['DB_USER'] = 'josh'
    os.environ['DB_PASSWORD'] = 'abcd1234'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '3306'
    os.environ['DB_NAMES'] = 'joshdb'
    os.environ['DB_TYPE'] = 'mysql'
    """
    
    env = ['DB_USER','DB_PASSWORD','DB_HOST', 'DB_PORT', 'DB_NAMES', 'DB_TYPE']

    def get_db_config():
        config=dict()
        conf = ['user','password','host','port', 'databases', 'type']
        try:
            config = {cnfVal: os.getenv(dbVal).rstrip() for dbVal,cnfVal in zip(env,conf)}
        except Exception as e:
            log.error(f'Missing an environment variable, {repr(e)}')
            config= {cnfVal: os.getenv(dbVal) for dbVal,cnfVal in zip(env,conf)}
            log.error(config)
            return config, 500
        return config, 200
    def attach(config):
        database = config['database']
        #try:
        if config['type'] == 'mysql':
            from mysql.connector import connect as connector
        else:
            import sqlite3.connect as connector
        server.data[database] = data.database(connector, **config)
        #TODO - add job to retry /internal/dbs/attach
        return {"message": f"db {database} attached successfully"}, 200
            
    @server.route('/internal/db/<database>/attach')
    def attach_database(database):
        config, rc = get_db_config()
        config['database'] = database
        return attach(config)

    @server.route('/internal/dbs/attach')
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
    
    response = attach_databases()
    log.warning(response)