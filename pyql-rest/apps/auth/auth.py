# auth
async def run(server):
    from fastapi import Request
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
    async def validate_user_pw(user, pw):
        user_sel = await server.data['pyql'].tables['authlocal'].select(
            'id', 
            'password', 
            where={'username': user}
        )
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
            async def check_auth(*args, **kwargs):
                request = kwargs['request']
                if not 'authentication' in kwargs:
                    token_type = 'PYQL_CLUSTER_TOKEN_KEY' if not location == 'local' else 'PYQL_LOCAL_TOKEN_KEY'
                    key = await server.env[token_type]

                    log.warning(f"checking auth from {check_auth.__name__} for {f} {args} {kwargs} {request.headers}")

                    if not 'authentication' in request.headers:
                        server.http_exception(401, log.error("missing 'authentication' in headers"))

                    auth = request.headers['authentication']

                    if 'Token' in auth:
                        token = auth.split(' ')[1].rstrip()
                        decoded_token = decode(token, key)

                        if decoded_token == None: 
                            server.http_exception(401, log.error(f"token authentication failed"))

                        kwargs['authentication'] = decoded_token['id']

                        if isinstance(decoded_token['expiration'], float):
                            if not decoded_token['expiration'] > time.time():
                                warning = f"token valid but expired for user with id {decoded_token['id']}"
                                server.http_exception(401, log.warning(warning))

                        log.warning(f"token auth successful for {kwargs['authentication']} using type {token_type} key {key}")
                        log.warning(f"check_auth - kwargs: {kwargs}")

                    # Basic Authentication Handling 
                    if 'Basic' in auth:
                        base64_cred = auth.split(' ')[1]
                        creds = base64.decodestring(base64_cred.encode('utf-8')).decode()
                        if not ':' in creds:
                            server.http_exception(
                                400,
                                "Basic authentication did not contain user pw separated by ':' Use: echo user:password | base64")
                        username, password = creds.split(':')
                        response, rc = await validate_user_pw(username, password)
                        if not rc == 200:
                            error = f"auth failed from {check_auth.__name__} for {f} - username {username}"
                            server.http_exception(401, log.error(error))
                        kwargs['authentication'] = response['userid']

                if location == 'local':
                    if await server.data['pyql'].tables['authlocal'][kwargs['authentication']] == None:
                        server.http_exception(403, log.error("un-authorized access"))
                    log.warning(f"local auth called using {kwargs['authentication']} finished")
                return await f(*args, **kwargs)
            check_auth.__name__ = '_'.join(str(uuid.uuid4()).split('-'))
            return check_auth
        return is_auth
    server.is_authenticated = is_authenticated

    @server.api_route('/auth/key/{location}', methods=['POST'])
    async def cluster_set_token_key(location: str, request: Request):
        return await set_token_key_auth(location)

    @server.is_authenticated('local')
    async def set_token_key_auth(location, **kw):
        return await set_token_key(location, value)

    async def set_token_key(location, value):
        """
        expects:
            location = cluster|local
            value = {'PYQL_LOCAL_TOKEN_KEY': 'key....'} | {'PYQL_CLUSTER_TOKEN_KEY': 'key....'}
        """
        if location == 'cluster' or location == 'local':
            key = f'PYQL_{location.upper()}_TOKEN_KEY'
            keydata = value
            if key in keydata:
                value = keydata[key]
                await server.env.set_item(key, value)
                return {"message": log.warning(f"{key} updated successfully with {value}")}
        server.http_exception(400, log.error("invalid location or key - specified"))

    if await server.env['PYQL_LOCAL_TOKEN_KEY'] == None:
        log.warning('creating PYQL_LOCAL_TOKEN_KEY')
        await set_token_key(  
            'local', 
            {
                'PYQL_LOCAL_TOKEN_KEY': ''.join(
                    random.choice(char_nums) for i in range(12)
                )
            }
        )
        log.warning(f"finished creating PYQL_LOCAL_TOKEN_KEY {await server.env['PYQL_LOCAL_TOKEN_KEY']}")
    else:
        log.warning(f'PYQL_LOCAL_TOKEN_KEY already existed {await server.env["PYQL_LOCAL_TOKEN_KEY"]}')

    async def create_auth_token(userid, expiration, location, extra_data=None):
        secret = await server.env[f'PYQL_{location.upper()}_TOKEN_KEY']
        data = {'id': userid, 'expiration': expiration}
        if expiration == 'join':
            data['create_time'] = time.time()
        if not extra_data == None:
            data.update(extra_data)
        token = encode(secret, **data)
        log.warning(f"create_auth_token created token {token} using {secret} from {location}")
        return token
    server.create_auth_token = create_auth_token
    
    # check for existing local pyql service user, create if not exists
    pyql_service_user = await server.data['pyql'].tables['authlocal'].select(
        '*', 
        where={'username': 'pyql'}
    )

    if len(pyql_service_user) == 0:
        service_id = str(uuid.uuid1())
        await server.data['pyql'].tables['authlocal'].insert(
            **{
                'id': service_id,
                'username': 'pyql',
                'type': 'service'
            }
        )
        log.warning(f"created new service account with id {service_id}")
        service_token = await create_auth_token(service_id, 'never', 'LOCAL')
        log.warning(f"created service account token {service_token}")

        # create user - if type stand-alone
        if os.environ.get('PYQL_TYPE') == 'STANDALONE':
            for var in ['PYQL_USER', 'PYQL_PASSWORD']:
                creds_provided = True
                if os.environ.get(var) == None:
                    creds_provided = False
            if creds_provided:
                await server.data['pyql'].tables['authlocal'].insert(
                    **{
                        'id': str(uuid.uuid1()),
                        'username': os.environ.get('PYQL_USER'), 
                        'password': encode_password(os.environ.get('PYQL_PASSWORD')),
                        'type': 'user'
                    }
                )
    else:
        log.warning(f"found existing service account")
        service_token = await create_auth_token(
            pyql_service_user[0]['id'], 
            'never', 'LOCAL'
        )
    # Local Token
    await server.env.set_item('PYQL_LOCAL_SERVICE_TOKEN', service_token)
        
    # Retrieve current local / cluster token - requires auth 
    @server.api_route('/auth/token/{token_type}')
    async def cluster_get_service_token(token_type: str, request: Request):
        return await get_service_token_auth(token_type)
    @server.is_authenticated('local')
    async def get_service_token_auth(token_type):
        return await get_service_token(token_type)
    async def get_service_token(token_type):
        if token_type == 'local':
            return {
                "PYQL_LOCAL_SERVICE_TOKEN": await server.env['PYQL_LOCAL_SERVICE_TOKEN']
                }

    # Retrieve current local / cluster token keys - requires auth 
    @server.api_route('/auth/key/{key_type}')
    async def cluster_set_service_token_key_auth(key_type: str, request: Request):
        return await set_service_token_key_auth(key_type)
    @server.is_authenticated('local')
    async def set_service_token_key_auth(key_type, **kw):
        return await set_service_token_key(key_type)

    @server.is_authenticated('local')
    async def set_service_token_key(key_type):
        if keytype == 'cluster':
            return {"PYQL_CLUSTER_TOKEN_KEY": await server.env['PYQL_CLUSTER_TOKEN_KEY']}, 200
        if keytype == 'local':
            return {"PYQL_LOCAL_TOKEN_KEY": await server.env['PYQL_LOCAL_TOKEN_KEY']}, 200
        return {"error": f"invalid token type specified {tokentype} - use cluster/local"}, 400