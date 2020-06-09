import os, unittest, json, requests, time, random, base64, subprocess

class rest:
    def __init__(self):
        self.steps = 0
        # loads 
        # {'clusterPort': 8090, 'clusterIp': '192.168.3.33', 'initAdminPw': 'YWRtaW46YWJjZDEyMzQ='}
        with open('test_pyql_rest_config.json', 'r') as config:
            self.config = json.loads(config.read())
        self.session = requests.Session()
        self.cluster = cluster(self)
        self.step = self.cluster.step
        self.simulations = {}
    def register_user(self):
        return self.cluster.probe('/auth/user/register', method='POST', data=self.config["user"])
    def is_running_simulations(self):
        for cluster in self.simulations:
            if time.time() -  self.simulations[cluster]['start'] < self.simulations[cluster]['duration']:
                return True
        return False
    def db_simulate(self, cluster, duration):
        assert cluster in self.cluster.clusters, f"{cluster} is missing or does not exist yet"
        if cluster in self.simulations:
            if time.time() -  self.simulations[cluster]['start'] < self.simulations[cluster]['duration']:
                print("cluster already has a running simulation")
                return
        else:
            self.simulations[cluster] = {}
        clusterIp = self.config['clusterIp']
        clusterPort = self.config['clusterPort']
        simulate = f"python db_simulator.py --host {clusterIp} --port {clusterPort} --cluster {cluster} --token {self.clusterToken} --duration {duration}"
        os.system(f"nohup {simulate} &")
        #subprocess.Popen(simulate.split(' '))
        self.simulations[cluster].update({'duration': duration, 'start': time.time()})

    def auth_setup(self):
        # Test Basic auth by pulling token from /auth/token/cluster
        self.step('test_auth - trying to pull clusterToken')
        self.auth = base64.encodebytes(
            f"{self.config['user']['username']}:{self.config['user']['password']}".encode('utf')
            ).decode().rstrip()
        
        assert not self.auth == None, f"auth is {self.auth}"
        print(f"auth is {self.auth}")
        token, rc = self.cluster.probe(
            f'/auth/token/user',
            auth={
                'method': 'basic', 'auth': self.auth
            }
        )
        assert rc == 200, f"error pulling user auth token {token} {rc}"
        print(f"token {token} rc {rc}")
        self.clusterToken = token['token']
        print(f"token pulled {self.clusterToken}")
    def docker_stop(self, cluster, port):
        assert cluster in self.cluster.clusters, f"{cluster} is missing or does not exist yet"
        for ports in self.cluster.clusters[cluster]:
            if ports[0] == port:
                os.system(f'docker container stop pyql-rest-{port}')
                return
        print(f"no instance with port {port} exists in cluster {cluster}")        
    def mass_expand_and_simulate(self, count, simulateDuration):
        for _ in range(count):
            for cluster in self.cluster.clusters:
                if cluster == 'index':
                    continue
                self.expand_data_cluster(cluster)
        self.step("mass_expand_and_simulate - pausing for 5 seconds for instances to join clusters")
        time.sleep(5)
        for cluster in self.cluster.clusters:
            if cluster == 'index':
                continue
            self.db_simulate(cluster, simulateDuration)
    def expand_data_cluster(self, cluster, token=None, port=None):
        clusterHost = self.cluster.config['clusterIp']
        clusterPort = self.cluster.config['clusterPort']
        token = self.joinToken if token == None else token
        # #Usage ./restart_pyql_rest.sh <tag> <local-port> <clusterhost:port> <db-port> <cluster> <init|join|test> [join token]
        if port == None:
            restPort = 8190 + self.cluster.clusters['index']
            restDbPort = 3330 + self.cluster.clusters['index']
            self.cluster.clusters['index']+=1
        else:
            for ports in self.cluster.clusters[cluster]:
                if ports[0] == port:
                    restPort, restDbPort = ports
                    break
        if not cluster in self.cluster.clusters:
            self.cluster.clusters[cluster] = [(restPort, restDbPort)]
            action = 'init'
        else:
            if port == None:
                self.cluster.clusters[cluster].append((restPort, restDbPort))
                action = 'join'
            else:
                action = 'rejoin'
                os.system(f'docker container stop pyql-rest-{restPort}')
                time.sleep(30)
        cache = '--no-cache' if action == 'init' else ''
        cmd = f'./restart_pyql_rest.sh dryrun.0.0 {restPort} {clusterHost}:{clusterPort} {clusterHost} {restDbPort} {cluster} {action} {token} {cache}'
        print(f"running cmd: {cmd}")
        os.system(cmd)
    def pull_join_token(self):
        self.step('test_auth - trying to pull join token for rest user')
        token, rc = self.cluster.probe(
            f'/auth/token/join',
            auth={
                'method': 'basic', 'auth': self.auth
            }
        )
        assert rc == 200, f"error pulling user auth token {token} {rc}"
        print(f"token {token} rc {rc}")
        self.joinToken = token['join']
        print(f"token pulled {self.joinToken}")

    def probe(self, path, **kw):
        clusterIp = self.config['clusterIp']
        clusterPort = self.config['clusterPort']
        kw['auth'] = {'method': 'token', 'auth': self.clusterToken} if not 'auth' in kw else kw['auth']
        kw['session'] = self.session
        return probe(f"http://{clusterIp}:{clusterPort}{path}", **kw)



class cluster:
    def __init__(self, rest):
        self.rest = rest
        # loads 
        # {'clusterPort': 8090, 'clusterIp': '192.168.3.33', 'initAdminPw': 'YWRtaW46YWJjZDEyMzQ='}
        self.config = self.rest.config
        self.session = self.rest.session
        self.auth_setup()
        self.clusters = {'index': 0}
    def step(self, action):
        print(f'starting step {self.rest.steps} - {action}')
        self.rest.steps+=1
    def auth_setup(self):
        # Test Basic auth by pulling token from /auth/token/cluster
        self.step('test_auth - trying to pull clusterToken')
        token, rc = self.probe(
            f'/auth/token/cluster',
            auth={
                'method': 'basic', 'auth': self.config['initAdminPw']
            }
        )
        print(f"token {token} rc {rc}")
        self.clusterToken = token['PYQL_CLUSTER_SERVICE_TOKEN']
        print(f"token pulled {self.clusterToken}")
    def docker_stop(self, port):
        assert port in self.nodes, f"cannot stop node pyql-cluster-{port}, not in list of started nodes"
        os.system(f"docker container stop pyql-cluster-{port}")
    def docker_restart(self, port):
        assert port in self.nodes, f"cannot restart node pyql-cluster-{port}, not in list of started nodes"
        os.system(f"docker container start pyql-cluster-{port}")
    def verify_data(self, tryCount=0):
        # for each cluster;
        clusters, rc = self.probe('/cluster/pyql/table/clusters/select')
        print(f"clusters {clusters}")
        for cluster in clusters['data']:
            # for each table in clusters
            tables, rc = self.probe(
                '/cluster/pyql/table/tables/select',
                method='POST',
                data={
                    'select': ['name'],
                    'where': {'cluster': cluster['id']}
                }
            )
            verify = {}
            #print(f"tables {tables}")
            for tb in tables['data']:
                table = tb['name']
                dataToVerify = {}
                # for each table endpoint - verify data
                tableEndpoints, rc = self.probe(f"/cluster/{cluster['id']}/table/{table}/endpoints")
                #print(f"tableEndpoints - {tableEndpoints}")
                for endpoint in tableEndpoints['inSync']:
                    endpointInfo = tableEndpoints['inSync'][endpoint]
                    dataToVerify[endpoint], rc = probe(
                        f"http://{endpointInfo['path']}/db/{endpointInfo['dbname']}/table/{table}/select",
                        auth={  
                            'method': 'token',
                            'auth': endpointInfo['token']
                        },
                        session=self.session
                    )
                    if rc == 200:
                        dataToVerify[endpoint] = dataToVerify[endpoint]['data']
                        #print(f"dataToVerify {dataToVerify[endpoint]}")
                    else:
                        assert False, f"dataToVerify ERROR  when acessing endpoint: {endpointInfo} table: {table} -- {dataToVerify[endpoint]}"
                verify[table] = {}
                for endpoint in dataToVerify:
                    verify[table][endpoint] = {'status': [], 'diff': {}}
                    for ep in dataToVerify:
                        if ep == endpoint:
                            continue
                        for t1r, t2r, in zip(dataToVerify[endpoint], dataToVerify[ep]):
                            if not t1r == t2r:
                                if not ep in verify[table][endpoint]['diff']:
                                    verify[table][endpoint]['diff'][ep] = []
                                verify[table][endpoint]['diff'][ep].append((t1r, t2r))
                                # every subsequent row will not be equal from here
                                break
                        if ep in verify[table][endpoint]['diff']:
                            verify[table][endpoint]['status'].append(False)
                            continue
                        verify[table][endpoint]['status'].append(True)
            
            verifyFail = []
            for table, endpoints in verify.items():
                for endpoint, status in endpoints.items():
                    if not table == 'jobs':
                        if False in status['status']: 
                            if tryCount < 2:
                                print(f"{table} endpoint {endpoint} data did not match with {status['diff'].keys()} - retrying")
                                time.sleep(5)
                                self.verify_data(tryCount+1)
                                return # avoid asserting if this is not the max retry run
                        if False in status['status']:
                            verifyFail.append(f"{table} endpoint {endpoint} data did not match with {status['diff']}")
            assert len(verifyFail) == 0, f"verification failed on endpoint(s) - {verifyFail}"
            print(f"verify completed for cluster {cluster['name']} - {verify}")



    def get_cluster_jobs(self, jobType=None):
        if jobType == None:
            return self.probe(
                '/cluster/pyql/table/jobs/select', 
                auth={'method': 'token', 'auth': self.clusterToken})
        return self.probe(
            '/cluster/pyql/table/jobs/select', method='POST',
            data={
                'select': ['*'], 'where': {
                    'type': jobType
                }
            },
            auth={'method': 'token', 'auth': self.clusterToken})
    def probe(self, path, **kw):
        clusterIp = self.config['clusterIp']
        clusterPort = self.config['clusterPort']
        kw['auth'] = {'method': 'token', 'auth': self.clusterToken} if not 'auth' in kw else kw['auth']
        kw['session'] = self.session
        return probe(f"http://{clusterIp}:{clusterPort}{path}", **kw)
    def sync_job_check(self):
        # checking for sync jobs
        maxCheck = 240 # should take less than 60 seconds for new sync jobs 
        start = time.time()
        while time.time() - start < maxCheck:
            jobs, rc = self.get_cluster_jobs()
            if rc == 200:
                jobs = [ job['type'] for job in jobs['data'] ]
            if 'syncjobs' in jobs:
                break
            print(f"waiting for sync jobs to start {jobs} - {time.time() - start:.2f}")
            time.sleep(5)
        assert 'syncjobs' in jobs, f"should take less than {maxCheck} seconds for new sync jobs"

        self.step('syncjobs detected, waiting for pyql tables to sync')
        time.sleep(10)
        maxSyncRunTimePerJob = 300
        startTime = time.time()
        lastCount = len(self.get_cluster_jobs('syncjobs')[0]['data'])
        lastJob = None
        while time.time() - startTime < maxSyncRunTimePerJob:
            jobs, rc = self.get_cluster_jobs('syncjobs')
            if rc == 200:
                if len(jobs['data']) < lastCount or len(jobs['data']) > lastCount:
                    lastCount = len(jobs['data'])
                    startTime = time.time()
                if len(jobs['data']) == 1:
                    if lastJob == jobs['data'][0]['id']:
                        continue
                    else:
                        lastJob = jobs['data'][0]['id']
                        lastCount = len(jobs['data'])
                        startTime = time.time()
                if lastCount == 0:
                    break
            print(f"waiting for {lastCount} sync jobs to complete {time.time() - startTime:.2f} sec")
            time.sleep(5)
        assert lastCount == 0, f"waited too long on a syncjobs job to finish - {time.time() - startTime:.2f}, {jobs}"
    def insync_and_state_check(self):
        """
        checks state of tables & querries sync_job_check until state is inSync True
        """
        self.step('verifying tables are properly synced on all endpoints')
        isOk = True
        limit, count = 10, 0
        while count < limit:
            try:
                stateCheck, rc = self.probe('/cluster/pyql/table/state/select')
                assert rc == 200, f"something wrong happened when checking state table {rc}"
                for state in stateCheck['data']:
                    if not state['inSync'] == True or not state['state'] == 'loaded':
                        print(f"found state which was not inSync=True & 'loaded {state}, retrying")
                        isOk = False
                        self.sync_job_check()
                        break
                if isOk:
                    break
                count+=1
            except Exception as e:
                print(f"something wrong happened when checking state table")
                break

def get_auth_http_headers(method, auth):
    headers = {'Accept': 'application/json', "Content-Type": "application/json"}
    if method == 'token':
        headers['Authentication'] = f'Token {auth}'
    else:
        headers['Authentication'] = f'Basic {auth}'
    return headers

def probe(path, method='GET', data=None, timeout=20.0, auth=None, **kw):
    action = requests if not 'session' in kw else kw['session']
    if 'method' in auth and 'auth' in auth:
        headers = get_auth_http_headers(**auth)
    try:
        if method == 'GET':
            r = action.get(f'{path}', headers=headers, timeout=timeout)
        else:
            r = action.post(f'{path}', headers=headers, data=json.dumps(data), timeout=timeout)
    except Exception as e:
        error = f"probe - Encountered exception when probing {path} - {repr(e)}"
        return error, 500
    try:
        return r.json(),r.status_code
    except:
        return r.text, r.status_code

#testCluster = cluster()
testRest = rest()


def test_expand_cluster(count):
    """
    count - number of nodes to expand cluster by 
    """
    joinToken, rc = testCluster.probe(
        f'/auth/token/join',
        auth={
            'method': 'basic', 'auth': testCluster.config['initAdminPw']
        }
    )
    testCluster.step("test_03_cluster_expansion - expanding cluster to test resync mechanisms & expandability")
    for _ in range(count):
        testCluster.expand_cluster(joinToken['join'])

    testCluster.step('wait 15 seconds and begin probing for "type": "syncjobs" jobs in jobs queue which are syncing newly added node')
    time.sleep(10)
    sync_job_check()

def sync_job_check():
    # checking for sync jobs
    maxCheck = 60 # should take less than 60 seconds for new sync jobs 
    start = time.time()
    while time.time() - start < maxCheck:
        jobs, rc = testCluster.get_cluster_jobs()
        if rc == 200:
            jobs = [ job['type'] for job in jobs['data'] ]
        if 'syncjobs' in jobs:
            break
        print(f"waiting for sync jobs to start {jobs}")
        time.sleep(5)
    assert 'syncjobs' in jobs, f"should take less than {maxCheck} seconds for new sync jobs"

    testCluster.step('syncjobs detected, waiting for pyql tables to sync')
    maxSyncRunTimePerJob = 45
    startTime = time.time()
    lastCount = len(testCluster.get_cluster_jobs('syncjobs')[0]['data'])
    while time.time() - startTime < maxSyncRunTimePerJob:
        jobs, rc = testCluster.get_cluster_jobs('syncjobs')
        if rc == 200:
            if len(jobs['data']) < lastCount or len(jobs['data']) > lastCount:
                lastCount = len(jobs['data'])
                startTime = time.time()
            if lastCount == 0:
                break
        print(f"waiting for {lastCount} sync jobs to complete {time.time() - startTime} sec")
        time.sleep(5)
    assert lastCount == 0, f"waited too long on a syncjobs job to finish, {jobs}"

class PyqlCluster(unittest.TestCase):
    def test_01_create_user_and_setup_auth(self):
        # Register new user - /auth/user/register
        result, rc = testRest.register_user() # This will return error 400 if already exists
        assert rc == 201, f"expected rc 201 - user created, but received {result} {rc}"

        # This is expected to fail as running twice
        result, rc = testRest.register_user()
        assert rc == 400, f"expected error 400 as user should aready have existed, maybe error in user creation {result} {rc}"
        # Pull user auth token
        testRest.auth_setup()
        testRest.pull_join_token()        
    def test_02_init_data_cluster(self):
        # using join token - init data clusters
        for cluster in ['data', 'data1', 'data2']:
            testRest.expand_data_cluster(cluster)
    def test_03_expand_data_clusters(self):
        testRest.mass_expand_and_simulate(2, 120)
        testRest.step("cluster expansion completed, waiting 10 seconds to begin monitoring table state & running sync jobs")
        time.sleep(10)
        testRest.cluster.insync_and_state_check()
        while testRest.is_running_simulations():
            print("waiting on running simulations to complete")
            time.sleep(10)
        testRest.cluster.verify_data()
    def test_04_node_down_and_resync_soft(self):
        """
        this tests the clusters ability to handle a node going down but
        not exactly while there is current load 'in-flight', tests recovery 
        during load
        """
        for cluster in testRest.cluster.clusters:
            if cluster == 'index':
                continue
            port = testRest.cluster.clusters[cluster][0][0]
            testRest.step(f'stopping cluster {cluster} node with port {port}')
            testRest.docker_stop(cluster, port)
            testRest.step(f"starting db_simulator on cluster {cluster}")
            testRest.db_simulate(cluster, 180)
        # restart nodes
        for cluster in testRest.cluster.clusters:
            if cluster == 'index':
                continue
            port = testRest.cluster.clusters[cluster][0][0]
            testRest.step(f'restarting cluster {cluster} node with port {port}')
            testRest.expand_data_cluster(cluster, port=port)
        testRest.step("restarted nodes, waiting 10 seconds to begin monitoring table state & running sync jobs")
        time.sleep(10)
        testRest.cluster.insync_and_state_check()
        while testRest.is_running_simulations():
            print("waiting on running simulations to complete")
            time.sleep(10)
        testRest.cluster.verify_data()
    def test_05_node_down_and_resync_hard(self):
        """
        this tests the clusters ability to handle a node going down
        while there are active transactions in-flight & recover properly
        while the same load is maintained
        """
        for cluster in testRest.cluster.clusters:
            if cluster == 'index':
                continue
            testRest.db_simulate(cluster, 240)
            port = testRest.cluster.clusters[cluster][0][0]
            testRest.step(f'stopping cluster {cluster} node with port {port} - during load')
            testRest.docker_stop(cluster, port)
        # restart nodes
        for cluster in testRest.cluster.clusters:
            if cluster == 'index':
                continue
            port = testRest.cluster.clusters[cluster][0][0]
            testRest.step(f'restarting cluster {cluster} node with port {port}')
            testRest.expand_data_cluster(cluster, port=port)
        testRest.step("restarted nodes, waiting 10 seconds to begin monitoring table state & running sync jobs")
        time.sleep(10)
        testRest.cluster.insync_and_state_check()
        while testRest.is_running_simulations():
            print("waiting on running simulations to complete")
            time.sleep(10)
        testRest.cluster.verify_data()