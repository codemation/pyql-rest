# internal
def run(server):
    import uuid
    log = server.log

    def db_check(database):
        db = server.data[database]
        if db.type == 'sqlite':
            result = db.get(f"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [t[0] for t in result]
            for r in result:
                log.info(f"db_check - found {r}")
        else:
            try:
                tables = db.get('show tables')
            except Exception as e:
                log.exception("error list tables")
                log.warning("trying to re-attach databases")
                server.attach_databases()
                tables = db.get('show tables')
            tables = [t[0] for t in tables]
            log.info(f"db_check result: {tables}")
            for table in tables:
                if not table in server.data[database].tables:
                    server.data[database].load_tables()
        return {"messages": log.info(f"{database} status ok"), "tables": tables}
    server.db_check = db_check
    
    def internal_job_add(job):
        jobId = str(uuid.uuid1())
        server.data['pyql'].tables['internaljobs'].insert(**{
            'id': jobId,
            'status': 'queued',
            'config': job
        })
    server.internal_job_add = internal_job_add

    @server.route('/internal/job/<id>/<action>', methods=['POST'])
    @server.is_authenticated('local')
    def internal_job_queue_action(id, action):
        if action == 'finished':
            server.data['pyql'].tables['internaljobs'].delete(where={'id': id})
        if action == 'queued':
            server.data['pyql'].tables['internaljobs'].update(status='queued', where={'id': id})
        return {"message": f"{action} on jobId {id} completed successfully"}, 200

    @server.route('/internal/job')
    @server.is_authenticated('local')
    def internal_job_queue_pull():
        jobs = server.data['pyql'].tables['internaljobs'].select('id', where={'status': 'queued'})
        if len(jobs) > 0:
            for job in jobs:
                server.data['pyql'].tables['internaljobs'].update(status='running', where={'id': job['id'], 'status': 'queued'})
                reserved = server.data['pyql'].tables['internaljobs'].select('*', where={'id': job['id'], 'status': 'running'})
                if len(reserved) == 1:
                    return {'id': job['id'], 'config': reserved[0]['config']}, 200
        return {"status": 200, "message": "no jobs in queue"}, 200
    @server.route('/internal/jobs')
    @server.is_authenticated('local')
    def internal_list_job_queue():
        return {'jobs': server.jobs}, 200
    @server.route('/internal/db/check')
    @server.is_authenticated('local')
    def internal_db_check():
        messages = []
        for database in server.data:
            messages.append(db_check(database))
        return {"result": messages if len(messages) > 0 else "No databases attached", "jobs": server.jobs}, 200
    @server.route('/internal/db/<database>/status')
    @server.is_authenticated('local')
    def internal_db_status(database):
        if database in server.data:
            return db_check(database), 200
        else:
            return {"status": 404, "message": f"database with name {database} not found"}, 404