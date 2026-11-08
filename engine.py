"""Thread-safe composition queue. Browser alone assigns and reports audio-clock bars."""
import contextvars
import copy
import threading
import time
import uuid
from .music import ROLES, controls, initial_session, number, pattern, validate_session
from .planning import Planner

class Jam:
    def __init__(self, ctx=None):
        self.ctx=ctx
        self.planner=Planner(ctx)
        self.lock=threading.RLock()
        self.session=initial_session()
        self.playing=False
        self.generation=0
        self.jobs={}
        self.phrase=[]
        self.clock={'bar':-1,'beat':0,'audio_time':0,'late_events':0}
        self.owner=None
        self.seen=0
        self.revisions={r:0 for r in ROLES}

    def status(self):
        with self.lock:
            s=copy.deepcopy(self.session)
            s.pop('performance')
            return dict(session=s,playing=self.playing,clock=self.clock,jobs=copy.deepcopy(list(self.jobs.values())[-20:]),
                        mode='Hermes role planners' if self.ctx else 'Local rule planners', recorded_bars=len(self.session['performance']),generation=self.generation)

    def queue(self, role, state, after=0, label='change', job=None):
        if len(self.session['pending']) >= 64: raise ValueError('Arrangement queue full')
        self.session['pending'].append(dict(id=uuid.uuid4().hex,role=role,state=copy.deepcopy(state),earliest=self.session['next_bar']+after,label=label,job=job))

    def configure(self, role, values, after=0, muted=None):
        if role not in ROLES: raise ValueError('Unknown musician')
        values=controls(values)
        after=number(after,0,64)
        if after != int(after): raise ValueError('Delay must be whole bars')
        if muted is not None and not isinstance(muted,bool): raise ValueError('Muted must be boolean')
        with self.lock:
            self.revisions[role]+=1
            state=copy.deepcopy(self.session['roles'][role])
            state['controls'].update(values)
            state['pattern']=pattern(role,state['controls'],state['motif'])
            state['intention']='Your controls, in the pocket.'
            if muted is not None: state['muted']=muted
            self.queue(role,state,after)
            return {'status':'waiting for audio buffer','role':role}

    def direct(self,text,lifecycle=None):
        if not isinstance(text,str) or not 1<=len(text.strip())<=2000: raise ValueError('Direction must be 1–2000 characters')
        with self.lock:
            if any(j['status']=='planning' for j in self.jobs.values()): raise ValueError('A direction is already planning; playback continues')
            ident=uuid.uuid4().hex
            self.jobs[ident]={'id':ident,'status':'planning','direction':text,'activations':[]}
            self.jobs=dict(list(self.jobs.items())[-20:])
            generation=self.generation
            revisions=self.revisions.copy()
            snapshot=copy.deepcopy(self.session)
            phrase=copy.deepcopy(self.phrase)
        def run():
            try:
                changes=self.planner.conduct(text,snapshot)
                if not isinstance(changes,list) or not 1<=len(changes)<=8: raise ValueError('Empty or oversized plan')
                prepared=[]
                for change in changes:
                    role=change['role']
                    if role not in ROLES: raise ValueError('Invalid musician')
                    state=copy.deepcopy(snapshot['roles'][role])
                    state['controls'].update(controls(change['controls']))
                    if not isinstance(change['muted'],bool): raise ValueError('Invalid mute')
                    state['muted']=change['muted']
                    state['intention']=str(change['intention'])[:240]
                    delay=number(change['after_bars'],0,64)
                    if int(delay)!=delay: raise ValueError('Invalid arrangement delay')
                    state['pattern']=self.planner.musician(role,state,snapshot,phrase,lifecycle)
                    prepared.append((role,state,int(delay)))
                with self.lock:
                    if generation!=self.generation or any(revisions[r]!=self.revisions[r] for r,_,_ in prepared):
                        self.jobs[ident]['status']='cancelled'; return
                    if len(self.session['pending'])+len(prepared)>64: raise ValueError('Arrangement queue full')
                    base=self.session['next_bar']
                    turnaround=(3-base%4)%4 if 'fill' in text.lower() else 0
                    for role,state,delay in prepared: self.queue(role,state,delay+turnaround,text,ident)
                    self.jobs[ident].update(status='waiting for audio buffer',earliest_bar=base+1)
            except Exception as exc:
                with self.lock:
                    # Do not expose provider errors: they can contain credentials or request bodies.
                    self.jobs[ident].update(status='failed — previous pattern continues',error=type(exc).__name__)
        context=contextvars.copy_context()
        threading.Thread(target=lambda:context.run(run),daemon=True,name='jam-composer').start()
        return {'job':ident,'status':'planning'}

    def start(self,owner):
        with self.lock:
            if self.playing and self.owner!=owner and time.monotonic()-self.seen<5: raise ValueError('Another browser is playing this jam')
            self.owner=owner; self.seen=time.monotonic(); self.playing=True
            return {'next_bar':self.session['next_bar'],'generation':self.generation}

    def stop(self):
        with self.lock:
            self.playing=False; self.generation+=1
            self.session['pending'].clear()
            for j in self.jobs.values():
                if j['status'] in ('planning','waiting for audio buffer','queued'): j['status']='cancelled'
                elif j['status']=='playing': j['status']='applied (stopped)'
            return {'status':'stopped','generation':self.generation}

    def bars(self,owner,start,count=1):
        number(start,0,100000); number(count,1,4)
        if int(start)!=start or int(count)!=count: raise ValueError('Whole bars required')
        with self.lock:
            if not self.playing or owner!=self.owner: raise ValueError('Start this browser first')
            self.seen=time.monotonic()
            if start!=self.session['next_bar']: raise ValueError('Bar frontier mismatch; restart transport')
            if len(self.session['performance'])+count>4096: raise ValueError('Session full; save and start a fresh jam')
            result=[]
            for bar in range(start,start+count):
                for change in list(self.session['pending']):
                    if change['earliest']>bar: continue
                    role=change['role']
                    history=self.session['history'][role]
                    if change['label'] != 'undo': history.append(copy.deepcopy(self.session['roles'][role]))
                    del history[:-64]
                    self.session['roles'][role]=change['state']
                    self.session['pending'].remove(change)
                    self.session['arrangement'].append({'role':role,'bar':bar,'label':change['label']})
                    del self.session['arrangement'][:-4096]
                    job=self.jobs.get(change.get('job'))
                    if job:
                        job['activations'].append({'role':role,'bar':bar+1}); job['status']='queued'
                record={'bar':bar,'tempo':self.session['tempo'],'roles':{},'human':[]}
                for role,state in self.session['roles'].items():
                    record['roles'][role]={'events':[] if state['muted'] else [copy.deepcopy(e) for e in state['pattern'] if e['bar']==bar%4], 'intention':state['intention']}
                result.append(record)
                self.session['performance'].append(copy.deepcopy(record))
            self.session['next_bar']=start+count
            return {'bars':result,'generation':self.generation}

    def heartbeat(self,owner,clock):
        for key,lo,hi in [('bar',-1,100000),('beat',0,4),('audio_time',0,1e9),('late_events',0,1e9)]: number(clock.get(key),lo,hi)
        with self.lock:
            if owner!=self.owner: raise ValueError('Not the playback browser')
            self.clock=clock; self.seen=time.monotonic()
            for job in self.jobs.values():
                if job['status']=='queued' and job['activations'] and max(a['bar'] for a in job['activations'])<=clock['bar']+1:
                    job['status']='playing'
            return self.status()

    def undo(self,role):
        if role not in ROLES: raise ValueError('Choose one musician')
        with self.lock:
            self.revisions[role]+=1
            pending=[p for p in self.session['pending'] if p['role']==role]
            if pending:
                self.session['pending']=[p for p in self.session['pending'] if p['role']!=role]
                return {'status':'cancelled pending changes','role':role}
            history=self.session['history'][role]
            if not history: raise ValueError('Nothing to undo for this musician')
            previous=history.pop()
            self.queue(role,previous,label='undo')
            return {'status':'undo waiting for audio buffer','role':role}

    def human(self,events):
        if not isinstance(events,list) or not 1<=len(events)<=64: raise ValueError('Phrase must contain 1–64 notes')
        clean=[]
        for e in events:
            pitch=number(e.get('pitch'),21,108)
            if int(pitch)!=pitch: raise ValueError('Integer MIDI pitch required')
            clean.append(dict(pitch=int(pitch),beat=number(e.get('beat'),0,3.999),duration=number(e.get('duration'),.04,4),velocity=number(e.get('velocity'),.01,1),bar=int(number(e.get('bar'),0,100000))))
        with self.lock:
            self.phrase=clean
            for e in clean:
                for bar in reversed(self.session['performance']):
                    if bar['bar']==e['bar']:
                        if len(bar['human'])<128: bar['human'].append(e)
                        break
        return {'status':'phrase ready','notes':len(clean)}

    def save(self):
        with self.lock: return copy.deepcopy(self.session)

    def restore(self,data):
        restored=validate_session(data)
        with self.lock:
            self.stop(); self.session=restored; self.jobs={}; self.phrase=[]; self.clock={'bar':-1,'beat':0,'audio_time':0,'late_events':0}
        return {'status':'restored, stopped','next_bar':restored['next_bar']}
