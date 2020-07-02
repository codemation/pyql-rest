# Used by workers for referencing db environ vars
import os
def get_db():
    config=dict()
    if 'PYQL_TYPE' in os.environ:
        if os.environ['PYQL_TYPE'] in ['K8S', 'STANDALONE']:
            db_location = os.environ['PYQL_VOLUME_PATH']
            config['database'] = f'{db_location}/pyql'
    else:
        with open('.cmddir', 'r') as proj_dir:
            for proj_path in proj_dir:
                config['database'] = f'{proj_path}dbs/pyql/pyql'
    from pyql import data
    import sqlite3
    db = data.Database(sqlite3.connect, **config)
    return db

def env():
    database = get_db()
    env = database.tables['env']
    def get_env_var(key):
        return env[key]
    return get_env_var