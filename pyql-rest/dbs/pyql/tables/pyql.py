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
                ('table_name', str),
                ('last_txn_uuid', str), 
                ('last_mod_time', float)
            ],
            'table_name'
            )
        #db_uuid = uuid.uuid1() 

    for database in server.data:
        if database == 'pyql':
            continue
        db_select = pyqldb.tables['pyql'].select('uuid','database', where={'database': database})
        if len(db_select) > 0:
            continue
        # DB did not exist yet in pyql table
        db_uuid = uuid.uuid1()
        for tb in server.data[database].tables:
            pyqldb.tables['pyql'].insert(**{
                'uuid': db_uuid,
                'database': database,
                'table_name': tb,
                'last_mod_time': time.time()
                })