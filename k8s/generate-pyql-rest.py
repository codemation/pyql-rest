import sys, os, base64

def get_base64_string(toEncode):
    base64Encoded = base64.encodestring(toEncode.encode('utf8')).decode().rstrip()
    if '\n' in base64Encoded:
        base64Encoded = ''.join(base64Encoded.split('\n'))
    return base64Encoded
def kubectl_apply_from_stdin(yaml):
    assert os.system(f"cat <<EOF | kubectl apply -f - {yaml}")== 0, f"kubectl_apply_from_stdin error applying config {yaml}"

def write_k8s_config_to_file(name, config):
    assert os.system(f"cat > {name} <<EOF {config}") == 0, f"error write_k8s_config_to_file for {name}"
    return name

def generate_seed_config(config):
    # pyql-cluster-config
    pyqlClusterConfig = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  creationTimestamp: null
  name: pyql-rest-cluster-config-{config['clusterid']}
data:
  PYQL_CLUSTER_SVC: {config['pyqlclustersvc']} # Include port via pyqlclustersvc:port if deployed in k8s cluster different than pyqlclustersvc
  PYQL_PORT: '{config['port']}' #default is 80
EOF
"""


    # pyql-rest-seed-db-config
    seedDbConfig =f"""
apiVersion: v1
kind: ConfigMap
metadata:
  creationTimestamp: null
  name: pyql-rest-seed-db-config-{config['clusterid']}-{config['tag']}
data:

  PYQL_CLUSTER_NAME: {config['clustername']}
  PYQL_CLUSTER_TABLES: {config['tables']}
  DB_TYPE: {config['dbtype']}
  DB_NAMES: {config['databases']}
EOF
"""
    ## pyql-rest-seed-db-secrets
    seedDbSecret = f"""
apiVersion: v1
kind: Secret
metadata:
  name: pyql-rest-seed-db-secrets-{config['clusterid']}-{config['tag']}
type: Opaque
data:
  DB_HOST: {get_base64_string(config['dbhost'])}
  DB_PORT: {get_base64_string(config['dbport'])}
  DB_USER: {get_base64_string(config['dbuser'])}
  DB_PASSWORD: {get_base64_string(config['dbpassword'])}
  PYQL_CLUSTER_JOIN_TOKEN: {get_base64_string(config['token'])}
EOF
"""
    ## pyql-rest-seed-pv
    seedPv = f"""
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pyql-rest-seed-pv-{config['clusterid']}-{config['tag']}
  labels:
    type: local
spec:
  storageClassName: pyql-rest-seed-sc-{config['clusterid']}-{config['tag']}
  capacity:
    storage: 20Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/pyql-rest-seed-pv-{config['clusterid']}-{config['tag']}
EOF
"""
    ## pyql-rest-seed-statefulSet
    def generate_statefulset(action):
        """
        expects action='init'|'join'
        """
        return f"""
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pyql-rest-seed-ss-{config['clusterid']}-{config['tag']}
spec:
  selector:
    matchLabels:
      app: pyql-rest-cluster-seed-{config['clusterid']}-{config['tag']} # has to match .spec.template.metadata.labels
  serviceName: pyql-rest-cluster-{config['clusterid']}
  replicas: 1 # by default is 1
  template:
    metadata:
      labels:
        app: pyql-rest-cluster-seed-{config['clusterid']}-{config['tag']} # has to match .spec.selector.matchLabels
        pyql-rest-cluster-id: {config['clusterid']}
        pyql-rest-cluster-name: {config['clustername']}
    spec:
      terminationGracePeriodSeconds: 5
      containers:
      - name: pyql-rest
        image: joshjamison/pyql-rest:latest
        env:
        - name: PYQL_CLUSTER_ACTION
          value: {action}
        envFrom:
        - configMapRef:
            name: pyql-rest-cluster-config-{config['clusterid']}
        - configMapRef:
            name: pyql-rest-seed-db-config-{config['clusterid']}-{config['tag']}
        - secretRef:
            name: pyql-rest-seed-db-secrets-{config['clusterid']}-{config['tag']}
        ports:
        - containerPort: 80
          name: http
        volumeMounts:
        - name: pyql-rest-seed-{config['clusterid']}-{config['tag']}
          mountPath: /mnt/pyql-rest
  volumeClaimTemplates:
  - metadata:
      name: pyql-rest-seed-{config['clusterid']}-{config['tag']}
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: pyql-rest-seed-sc-{config['clusterid']}-{config['tag']}
      resources:
        requests:
          storage: 20Gi
EOF
"""
    seedStatefulSetInit = generate_statefulset('init')
    seedStatefulSetJoin = generate_statefulset('join')

    # Write and apply configurations

    #pyqlClusterConfig
    pyqlClusterConfigYaml = f"pyql-rest-cluster-config-{config['clusterid']}-{config['tag']}.yaml"
    os.system(f"kubectl apply -f {write_k8s_config_to_file(pyqlClusterConfigYaml, pyqlClusterConfig)}")

    seedDbConfigYaml = f"pyql-rest-seed-db-config-{config['clusterid']}-{config['tag']}.yaml"
    os.system(f"kubectl apply -f {write_k8s_config_to_file(seedDbConfigYaml, seedDbConfig)}")

    seedPvYaml = f"pyql-rest-seed-pv-{config['clusterid']}-{config['tag']}.yaml"
    os.system(f"kubectl apply -f {write_k8s_config_to_file(seedPvYaml, seedPv)}")

    kubectl_apply_from_stdin(seedDbSecret)

    seedStatefulSetInitYaml = f"pyql-rest-cluster-seed-ss-init-{config['clusterid']}-{config['tag']}.yaml"
    write_k8s_config_to_file(seedStatefulSetInitYaml, seedStatefulSetInit)

    seedStatefulSetJoinYaml = f"pyql-rest-cluster-seed-ss-join-{config['clusterid']}-{config['tag']}.yaml"
    write_k8s_config_to_file(seedStatefulSetJoinYaml, seedStatefulSetJoin)

    ### Write Replica Configuration
    if config['dbtype'] == 'mysql':
        replicaMysqlSecret = f"""
apiVersion: v1
kind: Secret
metadata:
  creationTimestamp: null
  name: pyql-rest-replica-mysql-secrets-{config['clusterid']}
data:
  MYSQL_ROOT_PASSWORD: {get_base64_string(config['dbpassword'])}
  MYSQL_PASSWORD: {get_base64_string(config['dbpassword'])}
EOF
"""
        replicaMysqlConfig = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  creationTimestamp: null
  name: pyql-rest-replica-mysql-config-{config['clusterid']}
data:
  MYSQL_DATABASE: pyql_rest_{config['clustername']}_replica
  MYSQL_USER: {config['dbuser']}
  MYSQL_PORT: '3306'
EOF
"""
        replicaRestConfig = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  creationTimestamp: null
  name: pyql-rest-replica-config-{config['clusterid']}
data:
  PYQL_CLUSTER_NAME: {config['clustername']}
  PYQL_CLUSTER_TABLES: {config['tables']}
  DB_USER: {config['dbuser']}
  DB_HOST: 'localhost'
  DB_PORT: '3306'
  DB_NAMES: pyql_rest_{config['clustername']}_replica
  DB_TYPE: mysql
EOF
"""
        replicaRestSecrets = f"""
apiVersion: v1
kind: Secret
metadata:
  creationTimestamp: null
  name: pyql-rest-replica-secrets-{config['clusterid']}
data:
  DB_PASSWORD: {get_base64_string(config['dbpassword'])}
  PYQL_CLUSTER_JOIN_TOKEN: {get_base64_string(config['token'])}
"""

        replicaMysqlStatefulSet = f"""
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pyql-rest-replica-ss-{config['clusterid']}
spec:
  selector:
    matchLabels:
      app: pyql-rest-cluster-replica-{config['clusterid']} # has to match .spec.template.metadata.labels
  serviceName: "pyql-rest-replica"
  replicas: 2
  template:
    metadata:
      labels:
        app: pyql-rest-cluster-replica-{config['clusterid']} # has to match .spec.selector.matchLabels
        pyql-rest-cluster-id: {config['clusterid']}
        pyql-rest-cluster-name: {config['clustername']}
    spec:
      terminationGracePeriodSeconds: 5
      containers:
      - name: mysql
        image: joshjamison/mysql:latest
        envFrom:
          - configMapRef:
              name: pyql-rest-replica-mysql-config-{config['clusterid']}
          - secretRef:
              name: pyql-rest-replica-mysql-secrets-{config['clusterid']}
        ports:
        - name: http
          containerPort: 80
        - name: mysql
          containerPort: 3306
        volumeMounts:
        - name: pyql-rest-replica-mysql-store-{config['clusterid']}
          subPath: "mysql"
          mountPath: /var/lib/mysql
      - name: pyql-rest
        image: joshjamison/pyql-rest:latest
        env:
        - name: PYQL_CLUSTER_ACTION
          value: join
        envFrom:
        - configMapRef:
            name: pyql-rest-cluster-config-{config['clusterid']}
        - configMapRef:
            name: pyql-rest-replica-config-{config['clusterid']}
        - secretRef:
            name: pyql-rest-replica-secrets-{config['clusterid']}
        volumeMounts:
        - name: pyql-rest-replica-mysql-store-{config['clusterid']}
          mountPath: /mnt/pyql-rest
  volumeClaimTemplates:
  - metadata:
      name: pyql-rest-replica-mysql-store-{config['clusterid']}
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: pyql-rest-pv-manual-sc
      resources:
        requests:
          storage: 20Gi
EOF
"""     #replicaMysqlSecret
        kubectl_apply_from_stdin(replicaMysqlSecret)

        #replicaMysqlConfig
        replicaMysqlConfigYaml = f"pyql-rest-replica-mysql-config-{config['clusterid']}.yaml"
        os.system(f"kubectl apply -f {write_k8s_config_to_file(replicaMysqlConfigYaml, replicaMysqlConfig)}")

        #replicaRestConfig
        replicaRestConfigYaml = f"pyql-rest-replica-config-{config['clusterid']}.yaml"
        os.system(f"kubectl apply -f {write_k8s_config_to_file(replicaRestConfigYaml, replicaRestConfig)}")

        #replicaRestSecrets
        kubectl_apply_from_stdin(replicaRestSecrets)

        #replicaMysqlStatefulSet
        replicaMysqlStatefulSetYaml = f"pyql-rest-replica-ss-{config['clusterid']}.yaml"
        write_k8s_config_to_file(replicaMysqlStatefulSetYaml, replicaMysqlStatefulSet)



if __name__ == '__main__':
    expected = [
        '--clusterid', '--tables', 
        '--databases', '--dbtype', 
        '--dbuser', '--dbpassword',
        '--dbport', '--dbhost',
        '--token', '--clustername',
        '--port', '--pyqlclustersvc',
        '--tag']
    config = {}
    for arg in expected:
        assert arg in sys.argv, f"missing expected argument {arg}"
        assert len(sys.argv) -1 >= sys.argv.index(arg) +1, f"missing value for argument {arg}"
        argVal = sys.argv[sys.argv.index(arg)+1]
        assert not '--' in argVal, f"invalid value '{argVal}' provided for arg {arg}"
        config[arg[2:]] = argVal if not arg in ['--clusterid', '--tag'] else argVal.lower()
    generate_seed_config(config)