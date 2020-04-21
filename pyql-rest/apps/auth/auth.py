# auth
def run(server):
    from flask import request, make_response
    import os, uuid, time, json, base64, jwt, string, random
    charNums = string.ascii_letters + ''.join([str(i) for i in range(10)])
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
        userSel = server.clusters.auth.select('id', 'password', where={'username': user})
        if len(userSel) > 0:
            log.warning(f"checking auth for {userSel}")
            try:
                decoded = decode_password(userSel[0]['password'], pw)
                return {"message": f"Auth Ok", "userid": userSel[0]['id']}, 200
            except Exception as e:
                log.exception(f"Auth failed for user {user} - invalid credentials")
        return {"message": f"user / pw combination does not exist or is incorrect"}, 401
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
                    tokenType = 'PYQL_CLUSTER_TOKEN_KEY' if not location == 'local' else 'PYQL_LOCAL_TOKEN_KEY'
                    key = server.env[tokenType]
                    log.warning(f"checking auth from {check_auth.__name__} for {f} {args} {kwargs} {request.headers}")
                    if 'Authentication' in request.headers:
                        auth = request.headers['Authentication']
                        if 'Token' in auth:
                            token = auth.split(' ')[1].rstrip()
                            #decodedToken = decode(token, os.environ[tokenType])
                            decodedToken = decode(token, key)
                            if decodedToken == None:
                                error = f"token authentication failed"
                                log.error(error)
                                return {"error": error}
                            request.auth = decodedToken['id']
                            if 'join' in decodedToken['expiration']:
                                # Join tokens should only be used to join an endpoint to a cluster
                                if not 'join_cluster' in str(f):
                                    log.error(f"token authentication failed, join token auth attempted for {f}")
                                    error = f"invalid token supplied"
                                    return {"error": error}, 400
                            if isinstance(decodedToken['expiration'], float):
                                if not decodedToken['expiration'] > time.time():
                                    warning = f"token valid but expired for user with id {decodedToken['id']}"
                                    log.warining(warning)
                                    return {"error": warning}, 401 #TODO - Check returncode for token expiration
                            log.warning(f"token auth successful for {request.auth} using type {tokenType} key {key}")
                        if 'Basic' in auth:
                            base64Cred = auth.split(' ')[1]
                            creds = base64.decodestring(base64Cred.encode('utf-8')).decode()
                            if not ':' in creds:
                                return {
                                    "error": "Basic authentication did not contain user pw separated by ':' Use: echo user:password | base64"
                                    }, 400
                            username, password = creds.split(':')
                            response, rc = validate_user_pw(username, password)
                            if not rc == 200:
                                error = f"auth failed from {check_auth.__name__} for {f} - username {username}"
                                log.error(error)
                                return {"error": error}, 401
                            request.auth = response['userid']
                            # check if userid is a parent for other users

                        if location == 'local':
                            if not request.auth in server.data['pyql'].tables['authlocal']:
                                return {"error": "un-authorized access"}, 401
                            log.warining(f"local auth called using {request.auth} finished")
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
                log.warning(f"{key} updated successfully with {value}")
                return {"message": f"{key} updated successfully"}, 200
        return {"error": "invalid location or key - specified"}, 400

    if not 'PYQL_LOCAL_TOKEN_KEY' in server.env:
        log.warning('creating PYQL_LOCAL_TOKEN_KEY')
        r, rc = set_token_key(  
            'local', 
            {'PYQL_LOCAL_TOKEN_KEY': ''.join(random.choice(charNums) for i in range(12))}
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
    pyqlServiceUser = server.data['pyql'].tables['authlocal'].select('*', where={'username': 'pyql'})

    if not len(pyqlServiceUser) > 0:
        serviceId = str(uuid.uuid1())
        server.data['pyql'].tables['authlocal'].insert(**{
            'id': serviceId,
            'username': 'pyql',
            'type': 'service'
        })
        log.warning(f"created new service account with id {serviceId}")
        serviceToken = create_auth_token(serviceId, 'never', 'LOCAL')
        log.warning(f"created service account token {serviceToken}")
    else:
        log.warning(f"found existing service account")
        serviceToken = create_auth_token(
            pyqlServiceUser[0]['id'], 
            'never', 'LOCAL')
    # Local Token
    server.env['PYQL_LOCAL_SERVICE_TOKEN'] = serviceToken

        
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