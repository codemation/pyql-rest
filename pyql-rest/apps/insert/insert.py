# insert
def run(server):
    from flask import request
    log = server.log
    @server.route('/db/<database>/table/<table>/insert', methods=['POST'])
    @server.is_authenticated('local')
    def insert_func(database,table, params=None):
        message, rc = server.check_db_table_exist(database,table)
        if rc == 200:
            table = server.data[database].tables[table]
            params = request.get_json() if params == None else params
            data = {}
            for k,v in params.items(): 
                if not k in table.columns:
                    error = f"invalid key provided '{k}' not found in table {table.name}, valid keys {[col for col in table.columns]}"
                    return {"error": log.error(error)}, 400
            response = table.insert(**params)
            return {"message": "items added"}, 200
        else:
            return message, rc
    server.actions['insert'] = insert_func