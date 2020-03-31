# Used by workers for referencing db environ vars
import os
def get_db():
    config=dict()
    if 'PYQL_TYPE' in os.environ:
        if os.environ['PYQL_TYPE'] == 'K8S':
            dbLocation = os.environ['PYQL_VOLUME_PATH']
            config['database'] = f'{dbLocation}/pyql'
    else:
        with open('.cmddir', 'r') as projDir:
            for projectPath in projDir:
                config['database'] = f'{projectPath}dbs/pyql/pyql'
    from pyql import data
    import sqlite3
    db = data.database(sqlite3.connect, **config)
    return db

def env():
    database = get_db()
    env = database.tables['env']
    def get_env_var(key):
        return env[key]
    return get_env_var