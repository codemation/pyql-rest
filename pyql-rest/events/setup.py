def run(server):
    print("running events")

    from events.health import health
    health.run(server)