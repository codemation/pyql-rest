# auth
def run(server):
    from flask import request, make_response
    import os, uuid, time, json, base64, jwt, string, random
    char_nums = string.ascii_letters + ''.join([str(i) for i in range(10)])
    log = server.log
    def encode(secret, **kw):
        try:
            return jwt.encode(kw, secret, algorithm='HS256').decode()
        except Exception as e:
            log.exception(f"error encoding {kw} using {secret}")
    server.encode = encode
    def decode(token, secret):
        try:
            return jwt.decode(token.encode('utf-8'), secret, algorithm='HS256')
        except Exception as e:
            log.exception(f"error decoding token {token} using {secret}")

    def encode_password(pw):
        return encode(pw, password=pw, time=time.time())
    def decode_password(encodedPw, auth):
        return decode(encodedPw, auth)
    def validate_user_pw(user, pw):
        user_sel = server.data['pyql'].tables['authlocal'].select('id', 'password', where={'username': user})
        if len(user_sel) == 0:
            return {"message": f"user / pw combination does not exist or is incorrect"}, 401
        log.warning(f"checking auth for {user_sel}")
        try:
            decoded = decode_password(user_sel[0]['password'], pw)
            return {"message": f"Auth Ok", "userid": user_sel[0]['id']}, 200
        except Exception as e:
            return {"error": log.exception(f"Auth failed for user {user} - invalid credentials")}, 401
        
    def is_authenticated(location):
        """
        usage:
            @server.route('/')
            @is_authenticated('local') Or @is_authenticated('cluster')
            def home_func():
                #Add Code here
                print("Hello home World") 
                return {"message": "Hello home World"}, 200
        """
        def is_auth(f):
            def check_auth(*args, **kwargs):
                if not 'auth' in request.__dict__:
                    token_type = 'PYQL_CLUSTER_TOKEN_KEY' if not location == 'local' else 'PYQL_LOCAL_TOKEN_KEY'
                    key = server.env[token_type]
                    log.warning(f"checking auth from {check_auth.__name__} for {f} {args} {kwargs} {request.headers}")
                    if not 'Authentication' in request.headers:
                        return {"error": log.error("missing Authentication")}, 401
                    auth = request.headers['Authentication']
                    if 'Token' in auth:
                        token = auth.split(' ')[1].rstrip()
                        #decoded_token = decode(token, os.environ[token_type])
                        decoded_token = decode(token, key)
                        if decoded_token == None: 
                            return {"error": log.error("token authentication failed")}, 401
                        request.auth = decoded_token['id']
                        if 'join' in decoded_token['expiration']:
                            # Join tokens should only be used to join an endpoint to a cluster
                            if not 'join_cluster' in str(f):
                                return {"error": log.error(f"token authentication failed, join token auth attempted")}, 400
                        if isinstance(decoded_token['expiration'], float):
                            if not decoded_token['expiration'] > time.time():
                                warning = f"token valid but expired for user with id {decoded_token['id']}"
                                return {"error": log.warning(warning)}, 401 #TODO - Check returncode for token expiration
                        log.warning(f"token auth successful for {request.auth} using type {token_type} key {key}")
                    if 'Basic' in auth:
                        base64_cred = auth.split(' ')[1]
                        creds = base64.decodestring(base64_cred.encode('utf-8')).decode()
                        if not ':' in creds:
                            return {
                                "error": "Basic authentication did not contain user pw separated by ':' Use: echo user:password | base64"
                                }, 400
                        username, password = creds.split(':')
                        response, rc = validate_user_pw(username, password)
                        if not rc == 200:
                            error = f"auth failed from {check_auth.__name__} for {f} - username {username}"
                            return {"error": log.error(error)}, 401
                        request.auth = response['userid']
                        # check if userid is a parent for other users
                if location == 'local':
                    if not request.auth in server.data['pyql'].tables['authlocal']:
                        return {"error": log.error("un-authorized access")}, 401
                    log.warning(f"local auth called using {request.auth} finished")
                return f(*args, **kwargs)
            check_auth.__name__ = '_'.join(str(uuid.uuid4()).split('-'))
            return check_auth
        return is_auth
    server.is_authenticated = is_authenticated

    @server.route('/auth/key/<location>', methods=['POST'])
    @server.is_authenticated('local')
    def cluster_set_token_key(location):
        return set_token_key(location)
    def set_token_key(location, value=None):
        """
        expects:
            location = cluster|local
            value = {'PYQL_LOCAL_TOKEN_KEY': 'key....'} | {'PYQL_CLUSTER_TOKEN_KEY': 'key....'}
        """
        if location == 'cluster' or location == 'local':
            key = f'PYQL_{location.upper()}_TOKEN_KEY'
            keydata = request.get_json() if value == None else value
            if key in keydata:
                value = keydata[key]
                server.env[key] = value
                return {"message": log.warning(f"{key} updated successfully with {value}")}, 200
        return {"error": log.error("invalid location or key - specified")}, 400

    if not 'PYQL_LOCAL_TOKEN_KEY' in server.env:
        log.warning('creating PYQL_LOCAL_TOKEN_KEY')
        r, rc = set_token_key(  
            'local', 
            {'PYQL_LOCAL_TOKEN_KEY': ''.join(random.choice(char_nums) for i in range(12))}
            )
        log.warning(f"finished creating PYQL_LOCAL_TOKEN_KEY {server.env['PYQL_LOCAL_TOKEN_KEY']} - {r} {rc}")
    else:
        log.warning(f'PYQL_LOCAL_TOKEN_KEY already existed {server.env["PYQL_LOCAL_TOKEN_KEY"]}')

    def create_auth_token(userid, expiration, location):
        secret = server.env[f'PYQL_{location.upper()}_TOKEN_KEY']
        userid = userid if not expiration == 'join' else f'{userid}_join'
        data = {'id': userid, 'expiration': expiration}
        if expiration == 'join':
            data['createTime'] = time.time()
        token = encode(secret, **data)
        log.warning(f"create_auth_token created token {token} using {secret} from {location}")
        return token
    server.create_auth_token = create_auth_token
    
    # check for existing local pyql service user, create if not exists
    pyql_service_user = server.data['pyql'].tables['authlocal'].select('*', where={'username': 'pyql'})

    if len(pyql_service_user) == 0:
        service_id = str(uuid.uuid1())
        server.data['pyql'].tables['authlocal'].insert(**{
            'id': service_id,
            'username': 'pyql',
            'type': 'service'
        })
        log.warning(f"created new service account with id {service_id}")
        service_token = create_auth_token(service_id, 'never', 'LOCAL')
        log.warning(f"created service account token {service_token}")
        # create user - if type stand-alone
        if os.environ.get('PYQL_TYPE') == 'STANDALONE':
            for var in ['PYQL_USER', 'PYQL_PASSWORD']:
                creds_provided = True
                if os.environ.get(var) == None:
                    creds_provided = False
            if creds_provided:
                server.data['pyql'].tables['authlocal'].insert(**{
                    'id': str(uuid.uuid1()),
                    'username': os.environ.get('PYQL_USER'), 
                    'password': encode_password(os.environ.get('PYQL_PASSWORD')),
                    'type': 'user'
                })
    else:
        log.warning(f"found existing service account")
        service_token = create_auth_token(
            pyql_service_user[0]['id'], 
            'never', 'LOCAL')
    # Local Token
    server.env['PYQL_LOCAL_SERVICE_TOKEN'] = service_token

        
    # Retrieve current local / cluster token - requires auth 
    @server.route('/auth/token/<tokentype>')
    @server.is_authenticated('local')
    def cluster_service_token(tokentype):
        if tokentype == 'local':
            return {"PYQL_LOCAL_SERVICE_TOKEN": server.env['PYQL_LOCAL_SERVICE_TOKEN']}, 200

    # Retrieve current local / cluster token keys - requires auth 
    @server.route('/auth/key/<keytype>')
    @server.is_authenticated('cluster')
    def cluster_service_token_key(keytype):
        if keytype == 'cluster':
            return {"PYQL_CLUSTER_TOKEN_KEY": server.env['PYQL_CLUSTER_TOKEN_KEY']}, 200
        if keytype == 'local':
            return {"PYQL_LOCAL_TOKEN_KEY": server.env['PYQL_LOCAL_TOKEN_KEY']}, 200
        return {"error": f"invalid token type specified {tokentype} - use cluster/local"}, 400