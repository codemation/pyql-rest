# database - type mysql
def run(server):
    import sys, os
    
    os.environ['DB_USER'] = 'josh'
    os.environ['DB_PASSWORD'] = 'abcd1234'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '3306'
    os.environ['DB_NAME'] = 'joshdb'
    os.environ['DB_TYPE'] = 'mysql'


    @server.route('/internal/db/attach')
    def database_attach():
        config=dict()
            
        env = ['DB_USER','DB_PASSWORD','DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_TYPE']
        conf = ['user','password','host','port', 'database', 'type']
        try:
            config = {cnfVal: os.getenv(dbVal).rstrip() for dbVal,cnfVal in zip(env,conf)}
        except Exception as e:
            print('Missing an environment variable')
            config= {cnfVal: os.getenv(dbVal) for dbVal,cnfVal in zip(env,conf)}
            print(config)
            return {
                "status": 500, 
                "message": "Missing environment variable(s)",
                "required": env,
                "found": config
            }, 500 
        #USE ENV PATH for PYQL library or /pyql/
        #sys.path.append('/pyql/' if os.getenv('PYQL_PATH') == None else os.getenv('PYQL_PATH')) 
        # Can be removed because library will be installed using pip install pyql-db
        #
        try:
            from pyql import data
            import mysql.connector
            from . import setup
            server.data[config['database']] = data.database(mysql.connector.connect, **config)
            setup.attach_tables(server)
            return {"status": 200, "message": "database attached successfully"}, 200
        except Exception as e:
            error = repr(e)
            advice = ''
            if 'Access denied for user' in error:
                advice = f"""check if db "{config['database']}" exists and if user "{config['user']}" has permissions for the db"""
            return {"status": 500, "error": error, "message":advice}, 500
    
    try:
        response = database_attach()
        print(response)
    except Exception as e:
        print(repr(e))
        print("Unable to attach db right now, try again later using /database_attach")