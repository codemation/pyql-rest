
async def db_attach(server):
    db = server.data['pyql']
    if 'authlocal' in db:
        return
    await db.create_table(
       'authlocal', [
           ('id', str, 'UNIQUE NOT NULL'), 
           ('username', str, 'UNIQUE'),
           ('email', str, 'UNIQUE'),
           ('type', str), # admin / service / user
           ('password', str),
           ('parent', str) # uuid of parent, if service account or sub user account
        ],
        'id',
        cache_enabled=True
    )
    pass # Enter db.create_table statement here