# database - type mysql
def run(server):
    import os
    from pyql import data
    log = server.log
    
    os.environ['DB_USER'] = 'josh'
    os.environ['DB_PASSWORD'] = 'abcd1234'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '3306'
    os.environ['DB_NAMES'] = 'joshdb,joshdb2'
    os.environ['DB_TYPE'] = 'mysql'

    def get_db_config():
        config=dict()
        env = ['DB_USER','DB_PASSWORD','DB_HOST', 'DB_PORT', 'DB_NAMES', 'DB_TYPE']
        conf = ['user','password','host','port', 'databases', 'type']
        try:
            config = {cnfVal: os.getenv(dbVal).rstrip() for dbVal,cnfVal in zip(env,conf)}
        except Exception as e:
            print('Missing an environment variable')
            config= {cnfVal: os.getenv(dbVal) for dbVal,cnfVal in zip(env,conf)}
            print(config)
            return config, 500
        return config, 200
    def attach(config):
        database = config['database']
        try:
            if config['type'] == 'mysql':
                import mysql.connector as connector
            else:
                import sqlite3.connect as connector
            server.data[database] = data.database(connector, **config)
        except Exception as e:
            print(repr(e))
            error = repr(e)
            server.jobs.append({'type': 'GET', 'path': f'/internal/db/{database}/attach'})
            return {
                "message": f"Database Error during attach of db {database}, job queued for retry",
                "error": error
                }, 500
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
        try:
            from . import setup
            response = {'results': []}
            for database in config['databases'].split(','):
                errors = ''
                config['database'] = database
                result, rc = attach(config)
                response['results'].append({f'{database}': f'{result}'})
            setup.attach_tables(server)
            return response, 200
        except Exception as e:
            error = repr(e)
            advice = ''
            if 'Access denied for user' in error:
                advice = f"""check if dbs "{config['databases']}" exists and if user "{config['user']}" has permissions for the dbs"""
            return {"status": 500, "error": error, "message":advice}, 500
    
    try:
        response = attach_databases()
        print(response)
    except Exception as e:
        print(repr(e))
        print("Unable to attach db right now, will try again later")