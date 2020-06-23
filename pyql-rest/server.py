from flask import Flask
import os, socket
app = Flask(__name__)
def main(port):
    import setup
    setup.run(app)
    app.run('0.0.0.0', port, debug=True)
if __name__ == '__main__':
    try:
        import sys
        print(sys.argv)
        nodeName = sys.argv[1]
        port = sys.argv[2]
        cluster = sys.argv[3]
        clusterName = sys.argv[4]
        action = sys.argv[5]
        tables = sys.argv[6]
        token = sys.argv[7]
    except:
        print("expected input: ")
        print("python server.py <node-ip> <node-port> <clusterIp:port>")
    if not port == None:
        os.environ['PYQL_NODE'] = nodeName
        os.environ['PYQL_PORT'] = port
        os.environ['PYQL_CLUSTER_SVC'] = cluster
        os.environ['PYQL_CLUSTER_NAME'] = clusterName
        os.environ['PYQL_CLUSTER_ACTION'] = action
        os.environ['PYQL_CLUSTER_TABLES'] = tables
        os.environ['PYQL_CLUSTER_JOIN_TOKEN'] = token
        main(port)
else:
    # For loading when triggered by uWSGI
    if os.environ['PYQL_TYPE'] in ['K8S', 'STANDALONE']:
        os.environ['PYQL_NODE'] = socket.gethostbyname(socket.getfqdn())
        if os.environ['PYQL_TYPE'] == 'K8S':
            os.environ['PYQL_HOST'] = socket.gethostbyname(socket.getfqdn())

    import setup
    setup.run(app)