# Used by workers for referencing db environ vars
import os
def get_db():
    config=dict()
    with open('.cmddir', 'r') as projDir:
        for projectPath in projDir:
            dbName = os.getenv('DB_NAME').rstrip()
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