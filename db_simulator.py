import uuid, requests, sys, random, json, time
session = requests.Session()

def get_auth_http_headers(method, auth):
    headers = {'Accept': 'application/json', "Content-Type": "application/json"}
    if method == 'token':
        headers['Authentication'] = f'Token {auth}'
    else:
        headers['Authentication'] = f'Basic {auth}'
    return headers
def probe(path, method='GET', data=None, timeout=10.0, auth=None, **kw):
    if 'method' in auth and 'auth' in auth:
        headers = get_auth_http_headers(**auth)
    try:
        if method == 'GET':
            r = session.get(f'{path}', headers=headers, timeout=timeout)
        else:
            r = session.post(f'{path}', headers=headers, data=json.dumps(data), timeout=timeout)
    except Exception as e:
        error = f"probe - Encountered exception when probing {path} - {repr(e)}"
        return error, 500
    try:
        return r.json(),r.status_code
    except:
        return r.text, r.status_code


departments = [
    {'id': 1001, 'name': 'HR'},
    {'id': 2001, 'name': 'Sales'},
    {'id': 3001, 'name': 'Support'},
    {'id': 4001, 'name': 'Marketing'}
]

positions = [
    {'id': 100101, 'name': 'Director', 'departmentId': 1001},
    {'id': 100102, 'name': 'Manager', 'departmentId': 1001},
    {'id': 100103, 'name': 'Rep', 'departmentId': 1001},
    {'id': 100104, 'name': 'Intern', 'departmentId': 1001},
    {'id': 200101, 'name': 'Director', 'departmentId': 2001},
    {'id': 200102, 'name': 'Manager', 'departmentId': 2001},
    {'id': 200103, 'name': 'Rep', 'departmentId': 2001},
    {'id': 200104, 'name': 'Intern', 'departmentId': 2001},
    {'id': 300101, 'name': 'Director', 'departmentId': 3001},
    {'id': 300102, 'name': 'Manager', 'departmentId': 3001},
    {'id': 300103, 'name': 'Rep', 'departmentId': 3001},
    {'id': 300104, 'name': 'Intern', 'departmentId': 3001},
    {'id': 400101, 'name': 'Director', 'departmentId': 4001},
    {'id': 400102, 'name': 'Manager', 'departmentId': 4001},
    {'id': 400103, 'name': 'Rep', 'departmentId': 4001},
    {'id': 400104, 'name': 'Intern', 'departmentId': 4001}
]
positionChoices = [p['id'] for p in positions]



def get_random_name():
    name = ''
    fNames = ['Jane', 'Jill', 'Joe', 'John', 'Chris', 'Clara', 'Dale', 'Dana', 'Eli', 'Elly', 'Frank', 'George']
    lNames = ['Adams', 'Bale', 'Carson', 'Doe', 'Franklin','Smith', 'Wallace', 'Jacobs']
    fInd, lInd = random.randrange(len(fNames)-1), random.randrange(len(lNames)-1)
    return f"{fNames[fInd]} {lNames[lInd]}"

def get_random(choices):
    assert isinstance(choices, list), f'expected type list, found {type(choices)} for {choices}'
    return choices[random.randrange(len(choices))]

def simulate(host, port, cluster, duration, token):
    path = f'http://{host}:{port}/cluster/{cluster}/table/employees'
    def cluster_probe(location='', method='GET', data=None):
        return probe(
            f'{path}{location}', 
            method=method, 
            data=data,
            auth={
                'method': 'token',
                'auth': token
                }
        )
    latestEmployee = cluster_probe()
    assert not len(latestEmployee) < 1, f"error checking employees - {latestEmployee}"
    global employeeId
    employeeId = cluster_probe()[0]['data'][-1]['id'] +1
    
    def hire_employee():
        global employeeId
        name = get_random_name()
        position = get_random(positionChoices)
        data = {
                'id': employeeId, 
                'name': name, 
                'positionId': position}
        r, rc = cluster_probe('/insert', method='POST', data=data)
        #print(f"hire_employee id {employeeId} {name} {position} - {r} {rc}")
        employeeId+=1
    def transfer_employee():
        # pull all employees to transfer random employee
        listOfEmployees, rc = cluster_probe()
        #print(f"list of employees - {listOfEmployees}")
        randomEmp = get_random(listOfEmployees['data'])
        newPosition = get_random(positionChoices)
        data = {'positionId': get_random(positionChoices)}
        r, rc = cluster_probe(f"/{randomEmp['id']}", method='POST', data=data)
        #print(f"transfer_employee: {randomEmp['positionId']} --> {newPosition} - {r} {rc}")
    def fire_employee():
        listOfEmployees, rc = cluster_probe()
        #print(f"list of employees - {listOfEmployees}")
        randomEmp = get_random(listOfEmployees['data'])
        data = {'where': {'id': randomEmp['id']}}
        r, rc = cluster_probe(f"/delete", method='POST', data=data)
        #print(f"fire_employee - {r} {rc}")
    start = time.time()
    count = {'inserts': 0, 'updates': 0, 'deletes': 0}
    lastRun = None
    while time.time() - start < float(duration):
        if lastRun == fire_employee:
            event = hire_employee
        else:    
            event = get_random([hire_employee, transfer_employee, fire_employee])
        try:
            event()
            lastRun = event
            if event == hire_employee:
                count['inserts']+=1
            if event == transfer_employee:
                count['updates']+=1
            else:
                count['deletes']+=1
        except Exception as e:
            print(f"got exception when running {event} - {repr(e)}")
    print(f"cluster {cluster} simulated {count} in {duration} seconds")
if __name__ == '__main__':
    required = ['--host', '--port', '--cluster', '--duration', '--token']
    simArgs = {}
    for arg in required:
        assert arg in sys.argv, f"missing required {arg}"
        assert len(sys.argv) == len(required) * 2 +1, f"expected {len(required) * 2} arguments, found {len(sys.argv) -1} in {sys.argv}"
        assert not '--' in sys.argv[sys.argv.index(arg)+1], f"invalid input for {arg} - {sys.argv[sys.argv.index(arg)+1]}"
        simArgs[arg.split('--')[1]] = sys.argv[sys.argv.index(arg)+1]
    simulate(**simArgs)
     