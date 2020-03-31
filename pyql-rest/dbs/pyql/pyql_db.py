# pyql - type sqlite3
def run(server):
    import os
    from pyql import data
    import sqlite3
    from . import setup

    log = server.log
    @server.route('/internal/db/attach') # TODO - add @server.isauthenicated 
    def pyql_attach():
        config=dict()
        if 'PYQL_TYPE' in os.environ:
            if os.environ['PYQL_TYPE'] == 'K8S':
                dbLocation = os.environ['PYQL_VOLUME_PATH']
                config['database'] = f'{dbLocation}/pyql'
        else:
            with open('.cmddir', 'r') as projDir:
                for projectPath in projDir:
                    config['database'] = f'{projectPath}dbs/pyql/pyql'
        log.info("finished imports")
        server.data['pyql'] = data.database(sqlite3.connect, **config)
        log.info("finished dbsetup")
        setup.attach_tables(server)
        log.info("finished attach_tables")
        return {"status": 200, "message": f"database pyql attached successfully"}, 200
    response = pyql_attach()
    log.warning(response)