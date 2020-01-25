def run(server):
    import os
    import subprocess
    with open('.cmddir', 'r') as c:
        path = f'{([l for l in c][0])}events/health/'
    subprocess.Popen(['python', f'{path}checker.py', '/internal/db/check', '30.0', '/internal/db/attach'])