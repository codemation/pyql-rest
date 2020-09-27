import os, socket

from fastapi import FastAPI
app = FastAPI()

def main(port):
    import setup
    setup.run(app)
    app.run('0.0.0.0', port, debug=True)
if __name__ == '__main__':
    try:
        import sys
        print(sys.argv)
        NODE_NAME = sys.argv[1]
        PORT = sys.argv[2]
        CLUSTER_SVC = sys.argv[3]
        CLUSTER_NAME = sys.argv[4]
        CLUSTER_ACTION = sys.argv[5]
        CLUSTER_TABLES = sys.argv[6]
        JOIN_TOKEN = sys.argv[7]
    except:
        print("expected input: ")
        print("python server.py <node-ip> <node-port> <clusterIp:port>")
    if not port == None:
        os.environ['PYQL_NODE'] = NODE_NAME
        os.environ['PYQL_PORT'] = PORT
        os.environ['PYQL_CLUSTER_SVC'] = CLUSTER_SVC
        os.environ['PYQL_CLUSTER_NAME'] = CLUSTER_NAME
        os.environ['PYQL_CLUSTER_ACTION'] = CLUSTER_ACTION
        os.environ['PYQL_CLUSTER_TABLES'] = CLUSTER_TABLES
        os.environ['PYQL_CLUSTER_JOIN_TOKEN'] = JOIN_TOKEN
        main(PORT)
else:
    # For loading when triggered by uWSGI
    if os.environ.get('PYQL_TYPE') in ['K8S', 'STANDALONE']:
        os.environ['PYQL_NODE'] = socket.gethostbyname(socket.getfqdn())
        if os.environ['PYQL_TYPE'] == 'K8S':
            os.environ['PYQL_HOST'] = socket.gethostbyname(socket.getfqdn())
    else:
        # stand-alone
        #   env1="-e PYQL_HOST=192.168.1.10 -e PYQL_PORT=8090 -e PYQL_TYPE=STANDALONE 
        #  -e PYQL_USER=pyql_admin -e PYQL_PASSWORD='abcd1234' 
        #  -e DB_TYPE=sqlite3 -e DB_NAMES=company "
        os.environ['PYQL_NODE'] = '192.168.1.8'
        os.environ['PYQL_PORT'] = '8190'
        os.environ['PYQL_TYPE'] = 'STANDALONE'
        os.environ['PYQL_USER'] = 'pyql_admin'
        os.environ['PYQL_PASSWORD'] = 'abcd1234'
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['DB_NAMES'] = 'stocks'

    import setup
    setup.run(app)