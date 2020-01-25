def db_attach(server):
    db = server.data['pyql']
    db.create_table(
       'internaljobs', [
           ('id', str, 'UNIQUE NOT NULL'), 
           ('status', str), 
           ('config', str)
       ],
       'id'
    )