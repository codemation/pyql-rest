# pyql-rest
def run(server):
    import os
    ## LOAD ENV Vars & Default values
    environVars = [
            {'PYQL_DEBUG': False}
        ]
    for env in environVars:
        for e, v in env.items(): 
            if e in os.environ:
                t = type(v)
                try:
                    setattr(server, e, t(os.environ[e]))
                except Exception as e:
                    print(f"unable to set {e} from env vars, not a {t} capable value {os.environ[e]}, using default value {v}")
                    setattr(server, e, v)
            else:
                setattr(server, e, v)
    try:
        
        cmddirPath = None
        realPath = None
        with open('./.cmddir', 'r') as cmddir:
            for line in cmddir:
                cmddirPath = line
            realPath = str(os.path.realpath(cmddir.name)).split('.cmddir')[0]
        if not realPath == cmddirPath:
            print(f"NOTE: Project directory may have moved, updating project cmddir files from {cmddirPath} -> {realPath}")
            import os
            os.system("find . -name .cmddir > .proj_cmddirs")
            with open('.proj_cmddirs', 'r') as projCmdDirs:
                for f in projCmdDirs:
                    with open(f.rstrip(), 'w') as projCmd:
                        projCmd.write(realPath)
    except Exception as e:
        print("encountered exception when checking projPath")
        print(repr(e))
    #try:
    server.jobs = []
    from logs import setup as log_setup
    log_setup.run(server)
    from dbs import setup as db_setup # TOO DOO -Change func name later
    db_setup.run(server) # TOO DOO - Change func name later
    from apps import setup
    setup.run(server)
    from events import setup as event_setup
    event_setup.run(server)