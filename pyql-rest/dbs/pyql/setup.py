 # pyql
async def attach_tables(server):
    from dbs.pyql.tables import internaljobs
    await internaljobs.db_attach(server)
            
    from dbs.pyql.tables import auth
    await auth.db_attach(server)
            
    from dbs.pyql.tables import env
    await env.db_attach(server)
            
    from dbs.pyql.tables import pyql
    await pyql.db_attach(server)