# pyql - type sqlite3
def run(server):
    """
    import sys, os
    @server.route('/pyql_attach')
    def pyql_attach():
        config=dict()
            
        with open('.cmddir', 'r') as projDir:
            for projectPath in projDir:
                config['database'] = f'{projectPath}dbs/pyql/pyql'
        #USE ENV PATH for PYQL library or /pyql/
        sys.path.append('/pyql/' if os.getenv('PYQL_PATH') == None else os.getenv('PYQL_PATH'))
        try:
            import data, sqlite3
            from . import setup
            server.data['pyql'] = data.database(sqlite3.connect, **config)
            setup.attach_tables(server)
            return {"status": 200, "message": "pyql attached successfully"}, 200
        except Exception as e:
            return {"status": 200, "message": repr(e)}, 500
    pyql_attach()
    """

    import sys, os
    log = server.log
    @server.route('/internal/db/attach')
    def pyql_attach():
        config=dict()
        os.environ['DB_NAME'] = 'pyql' # TODO - Add to env variables config later
        dbname = os.environ['DB_NAME'] # TODO - Add to env variables config later
        if 'PYQL_TYPE' in os.environ:
            if os.environ['PYQL_TYPE'] == 'K8S':
                dbLocation = os.environ['PYQL_VOLUME_PATH']
                config['database'] = f'{dbLocation}/{dbname}'
        else:
            with open('.cmddir', 'r') as projDir:
                for projectPath in projDir:
                    config['database'] = f'{projectPath}dbs/pyql/{dbname}'
        #USE ENV PATH for PYQL library or /pyql/
        #sys.path.append('/pyql/' if os.getenv('PYQL_PATH') == None else os.getenv('PYQL_PATH'))
        #try:
        from pyql import data
        import sqlite3
        from . import setup
        log.info("finished imports")
        server.data[dbname] = data.database(sqlite3.connect, **config)
        log.info("finished dbsetup")
        setup.attach_tables(server)
        log.info("finished attach_tables")
        return {"status": 200, "message": f"database {dbname} attached successfully"}, 200
        #except Exception as e:
        #    return {"status": 200, "message": repr(e)}, 500
    response = pyql_attach()
    log.warning(response)