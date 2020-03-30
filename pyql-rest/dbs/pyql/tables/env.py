def db_attach(server):
    db = server.data['pyql']
    db.create_table(
       'env', [
           ('env', str, 'UNIQUE NOT NULL'), 
           ('val', str)
       ],
       'env'
    )
    server.env = db.tables['env']