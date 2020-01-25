def db_attach(server):
    db = server.data['pyql']
    db.create_table(
       'cache', [
           ('id', str, 'UNIQUE NOT NULL'), 
           ('type', str), 
           ('txn', str)
       ],
       'id'
    )