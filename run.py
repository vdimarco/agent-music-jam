"""Standalone local-rule rehearsal mode; no credentials or model access."""
import importlib.util
import pathlib
import sys
import time

if __name__=='__main__':
    root=pathlib.Path(__file__).parent
    spec=importlib.util.spec_from_file_location('agent_music_jam',root/'__init__.py',submodule_search_locations=[str(root)])
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    service=module.Service(port=int(sys.argv[1]) if len(sys.argv)>1 else 0)
    print(service.url,flush=True)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: service.close()
