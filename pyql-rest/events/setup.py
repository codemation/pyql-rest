def run(server):
    from events.health import health
    health.run(server)
    from events.jobs import jobs
    jobs.run(server)