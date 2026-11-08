"""Agent Music Jam — native Hermes registration, inert until jam_start."""
import json
import threading
from .server import Service

TOOLS = {
 'jam_start':('Open the local band interface. Audio requires clicking Play in the browser.',{}),
 'jam_inspect':('Inspect musician intentions, queued activation bars and playback.',{}),
 'jam_stop':('Stop playback and cancel all pending composition changes.',{}),
 'jam_direct':('Direct musicians with natural language. Plans asynchronously; inspect for actual activation bars.',{'text':{'type':'string'}}),
 'jam_configure':('Adjust one musician; preserve other parts. Controls 0..1 except register -12..12.',{'role':{'type':'string','enum':['drums','bass','keys','lead']},'controls':{'type':'object'}}),
 'jam_schedule':('Schedule a musician change after N bars beyond the next available audio buffer boundary.',{'role':{'type':'string','enum':['drums','bass','keys','lead']},'controls':{'type':'object'},'after_bars':{'type':'integer','minimum':0,'maximum':64},'muted':{'type':'boolean'}}),
 'jam_undo':('Undo only the chosen musician, quantized to the next available bar.',{'role':{'type':'string','enum':['drums','bass','keys','lead']}}),
 'jam_save':('Save the complete musical session in profile-scoped plugin state.',{}),
 'jam_restore':('Restore the last saved session, stopped.',{}),
 'jam_export':('Export MIDI or download the browser’s actual recorded WAV audio. Requires open band browser.',{'format':{'type':'string','enum':['midi','wav']}}),
}

def register(ctx):
    lock=threading.Lock()
    service=None
    def get_service():
        nonlocal service
        with lock:
            if service is None: service=Service(ctx,ctx.get_config('port',0))
            return service
    def handle(name,args,**kwargs):
        try:
            if name=='jam_start':
                s=get_service()
                return json.dumps({'url':s.url,'status':'waiting for browser Play','note':'Local access link is private; do not include it in exports.'})
            if service is None: return json.dumps({'error':'Start a jam first'})
            s=service
            if name=='jam_direct':
                lifecycle=None
                if ctx.get_config('use_subagents',True):
                    # Only Hermes tool calls have a parent turn; browser calls use role planners.
                    lifecycle=getattr(ctx,'subagent_lifecycle',None)
                result=s.jam.direct(args['text'],lifecycle)
            elif name=='jam_restore':
                data=ctx.state.get('saved_session',default=None)
                if data is None: raise ValueError('No saved session')
                result=s.jam.restore(data)
            elif name=='jam_export':
                with s.jam.lock: s.actions.append({'type':'export','format':args['format']})
                result={'status':'download requested in browser','format':args['format']}
            else:
                action={'jam_inspect':'status','jam_schedule':'configure','jam_configure':'configure','jam_undo':'undo','jam_stop':'stop','jam_save':'save'}[name]
                result=s.call(action,args)
                if name=='jam_save': result={'status':'saved','bars':len(result['performance'])}
            return json.dumps(result)
        except Exception as exc:
            return json.dumps({'error':type(exc).__name__,'message':'Jam operation failed; inspect the band or check configuration.'})
    for name,(description,properties) in TOOLS.items():
        schema={'name':name,'description':description,'parameters':{'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}}
        ctx.register_tool(name=name,toolset='agent_music_jam',schema=schema,handler=lambda args,_name=name,**kw:handle(_name,args,**kw))
    def close():
        if service: service.close()
    ctx.on_unload(close)
