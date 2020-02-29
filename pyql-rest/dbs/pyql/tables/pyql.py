def db_attach(server):
    """
        special table added to all dbs in server.data for id / state tracking
    """
    import uuid, time
    pyqldb = server.data['pyql']
    if not 'pyql' in pyqldb.tables:
        pyqldb.create_table(
            'pyql', 
            [
                ('uuid', str), 
                ('database', str),
                ('tableName', str),
                ('lastTxnUuid', str), 
                ('lastModTime', float)
            ],
            'tableName'
            )
        #dbUuid = uuid.uuid1() 

    for database in server.data:
        if database == 'pyql':
            continue
        dbSelect = pyqldb.tables['pyql'].select('uuid','database', where={'database': database})
        if len(dbSelect) > 0:
            continue
        # DB did not exist yet in pyql table
        dbUuid = uuid.uuid1()
        for tb in server.data[database].tables:
            pyqldb.tables['pyql'].insert(**{
                'uuid': dbUuid,
                'database': database,
                'tableName': tb,
                'lastModTime': time.time()
                })