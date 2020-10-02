async def db_attach(server):
    db = server.data['pyql']
    if 'env' in db:
        return
    await db.create_table(
       'env', [
           ('env', str, 'UNIQUE NOT NULL'), 
           ('val', str)
       ],
       'env',
       cache_enabled=True
    )
    server.env = db.tables['env']