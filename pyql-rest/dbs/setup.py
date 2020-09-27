
async def run(server):
    server.data = dict()
    from dbs.database import database_db
    await database_db.run(server)
    from dbs.pyql import pyql_db
    await pyql_db.run(server)
            