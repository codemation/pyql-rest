import sys, time, requests

def probe(endpoint):
    """
        default staring is http://localhost:8080
    """
    url = f'http://localhost:8080{endpoint}'
    try:
        r = requests.get(url, headers={'Accept': 'application/json'}, timeout=1.0)
        try:
            return r.json(),r.status_code
        except:
            return r.text, r.status_code
    except Exception as e:
        print(f"checker.py Exception encountered while checking {endpoint}")
        return {"error": f"{repr(e)}"}, 500


if __name__=='__main__':
    args = sys.argv
    if len(args) > 3:
        endpoint, delay, action  = args[1], float(args[2]), args[3]
        start = delay
        while True:
            time.sleep(1)
            if delay < time.time() - start:
                message, rc = probe(endpoint)
                print(rc)
                if action == 'job':
                    try:
                        message, rc = probe(message['path'])
                        print(f"job result: {message}")
                else:
                    if not rc == 200:
                        message, rc = probe(action)
                        print(message, rc)
                print(message)
                start = time.time()