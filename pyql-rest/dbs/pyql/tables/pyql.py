async def db_attach(server):
    """
        special table added to all dbs in server.data for id / state tracking
    """
    import uuid, time, asyncio
    
    print(f"attaching pyql table within db pyql")
    db = server.data['pyql']
    if not 'pyql' in db.tables:
        await db.create_table(
        'pyql', 
        [
            ('uuid', str), 
            ('database', str),
            ('table_name', str),
            ('last_txn_uuid', str), 
            ('last_txn_time', float),
            ('lock_id', str)
        ],
        'table_name',
        cache_enabled=True
        )
    for database in server.data:
        if database == 'pyql':
            continue
        db_uuid = str(uuid.uuid1())
        insert_coros = []
        for tb in server.data[database].tables:
            insert_coros.append(db.tables['pyql'].insert(
                **{
                    'uuid': db_uuid,
                    'database': database,
                    'table_name': tb,
                    'last_txn_time': time.time()
                    })
            )
        await asyncio.gather(*insert_coros)
    return # Enter db.create_table statement here