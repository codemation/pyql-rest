def run(server):
    from flask import request
    import os, uuid, time, json
    log = server.log
    TXN_DEFAULT_WAIT_IN_SEC = 0.005     # default 5 ms
    TXN_MAX_WAIT_INTERVAL_IN_SEC = 0.050 # 50 ms
    TXN_MAX_WAIT_TIME_IN_SEC = 0.550     # 550 ms
    cache = server.data['pyql'].tables['cache']
    # pull stats from docker instance
    # docker logs -f pyql-cluster-8090 2>&1 | grep '##cache commit' | grep 'WARNING' | awk '{print  $8" "$9" "$10" "$12}'

    @server.route('/db/<database>/cache/<table>/txn/<action>', methods=['POST'])
    @server.is_authenticated('local')
    def cache_txn_manage(database, table, action, trans=None, **kw):
        """
            method for managing txns - canceling / commiting
        """
        transaction = request.get_json() if trans == None else trans
        if 'txn' in transaction:
            txn_id = transaction['txn']
            tx=None
            wait_time = 0.0                      # total time waiting to commit txn 
            wait_interval = TXN_DEFAULT_WAIT_IN_SEC  # amount of time to wait between checks - if multiple txns exist 
            # Get transaction from cache db
            if action == 'commit':
                while True:
                    txns = cache.select('id','timestamp',
                        where={'table_name': table}
                    )
                    if not txn_id in {tx['id'] for tx in txns}:
                        return {"message": log.error(f"{txn_id} does not exist in cache")}, 500
                    if len(txns) == 1:
                        if not txns[0]['id'] == txn_id:
                            warning = f"txn with id {txn_id} does not exist for {database} {table}"
                            return {'warning': log.warning(warning)}, 500
                        # txn_id is only value inside
                        tx = txns[0]
                        break
                    # multiple pending txns - need to check timestamp to verify if this txn can be commited yet
                    txns = sorted(txns, key=lambda txn: txn['timestamp'])
                    for ind, txn in enumerate(txns):
                        if txn['id'] == txn_id:
                            if ind == 0:
                                tx = txns[0]
                                break
                            if wait_time > TXN_MAX_WAIT_TIME_IN_SEC:
                                warning = f"timeout of {wait_time} reached while waiting to commit {txn_id} for {database} {table}, waiting on {txns[:ind]}"
                                log.warning(warning)
                                log.warning(f"removing txn with id {txns[0]['id']} maxWaitTime of {TXN_MAX_WAIT_TIME_IN_SEC} reached")
                                cache.delete(where={'id': txns[0]['id']})
                                break
                            break
                    if tx == None:
                        log.warning(f"txn_id {txn_id} is behind txns {txns[:ind]} - waiting {wait_time} to retry")
                        time.sleep(wait_interval)
                        wait_time+=wait_interval 
                        # wait_interval scales up to TXN_MAX_WAIT_INTERVAL_IN_SEC
                        wait_interval+=wait_interval 
                        if wait_interval >= TXN_MAX_WAIT_INTERVAL_IN_SEC:
                            wait_interval = TXN_MAX_WAIT_INTERVAL_IN_SEC
                        continue
                    break
                # Should not have broken out of loop here without a tx
                if tx == None:
                    log.error("tx is None, this should not hppen")
                    return {"error": "tx was none"}, 500
                tx = cache.select('type','txn',
                        where={'id': txn_id})[0]
                try:
                    r, rc = server.actions[tx['type']](database, table, tx['txn'])
                    log.warning(f"##cache {action} response {r} rc {rc}")
                except Exception as e:
                    r, rc = log.exception(f"Exception when performing cache {action}"), 500
                
                del_txn = cache.delete(
                    where={'id': txn_id}
                )
                if rc == 200:
                    # update last txn id
                    setParams = {
                        'set': {
                            'last_txn_uuid': txn_id,
                            'last_mod_time': float(time.time())
                            },
                        'where': {
                            'table_name': table
                        }
                    }
                    server.data['pyql'].tables['pyql'].update(
                            **setParams['set'],
                            where=setParams['where']
                    )
                return {"message": r, "status": rc}, rc
            if action == 'cancel':
                del_txn = cache.delete(
                    where={'id': txn_id}
                )
                return {'deleted': txn_id}, 200
    @server.route('/db/<database>/cache/<table>/<action>/<txuuid>', methods=['POST'])
    @server.is_authenticated('local')
    def cache_action(database, table, action,txuuid):
        transaction = request.get_json()
        server.data['pyql'].tables['cache'].insert(**{
            'id': txuuid,
            'table_name': table,
            'type': action,
            'timestamp': transaction['time'],
            'txn': transaction['txn']
        })
        return {"txn": txuuid}, 200