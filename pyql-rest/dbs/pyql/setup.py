 # pyql
def attach_tables(server):

    from dbs.pyql.tables import cache
    cache.db_attach(server)
            
    from dbs.pyql.tables import internaljobs
    internaljobs.db_attach(server)
            
    from dbs.pyql.tables import auth
    auth.db_attach(server)
            
    from dbs.pyql.tables import env
    env.db_attach(server)
            
    from dbs.pyql.tables import pyql
    pyql.db_attach(server)