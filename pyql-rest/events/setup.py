def run(server):
    import os
    from events.health import health
    health.run(server)
    if os.environ.get('PYQL_TYPE') == 'K8S':
        from events.jobs import jobs
        jobs.run(server)