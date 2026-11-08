"""Loopback-only, token-authenticated local service. No third-party web assets."""
import base64
import hmac
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .engine import Jam
from .music import midi, validate_pattern, ROLES, number, validate_browser

class Service:
    def __init__(self,ctx=None,port=0):
        self.jam=Jam(ctx)
        self.token=secrets.token_urlsafe(32)
        self.actions=[]
        outer=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def reply(self,data,status=200,mime='application/json'):
                body=json.dumps(data,allow_nan=False).encode() if mime=='application/json' else data
                self.send_response(status)
                self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(len(body)))
                self.send_header('Cache-Control','no-store')
                self.send_header('Referrer-Policy','no-referrer')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
                self.end_headers(); self.wfile.write(body)
            def valid_host(self):
                return self.headers.get('Host')==f'127.0.0.1:{outer.server.server_port}'
            def do_GET(self):
                if not self.valid_host(): return self.reply({'error':'Invalid host'},403)
                paths={'/':'index.html','/app.js':'app.js','/audio.js':'audio.js','/recorder.js':'recorder.js','/style.css':'style.css'}
                path=paths.get(self.path)
                if not path: return self.reply({'error':'Not found'},404)
                mime={'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[path.split('.')[-1]]
                self.reply((Path(__file__).parent/'web'/path).read_bytes(),mime=mime)
            def do_POST(self):
                if not self.valid_host(): return self.reply({'error':'Invalid host'},403)
                origin=self.headers.get('Origin')
                if origin and origin!=outer.origin: return self.reply({'error':'Invalid origin'},403)
                if not hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer '+outer.token): return self.reply({'error':'Unauthorized'},401)
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=8_000_000: raise ValueError('Request too large or empty')
                    data=json.loads(self.rfile.read(size))
                    if not isinstance(data,dict): raise ValueError('JSON object required')
                    result=outer.call(self.path.removeprefix('/api/'),data)
                    self.reply(result)
                except (ValueError,KeyError,TypeError,OverflowError) as exc: self.reply({'error':str(exc)},400)
                except Exception: self.reply({'error':'Operation failed; previous session preserved'},500)
        self.server=ThreadingHTTPServer(('127.0.0.1',int(port)),Handler)
        self.server.daemon_threads=True
        self.origin=f'http://127.0.0.1:{self.server.server_port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True,name='jam-loopback')
        self.thread.start()

    @property
    def url(self): return self.origin+'/#'+self.token

    def close(self):
        self.jam.stop(); self.server.shutdown(); self.server.server_close()

    def call(self,action,d):
        jam=self.jam
        if action=='status':
            result=jam.status()
            with jam.lock:
                result['actions']=self.actions[:] if d.get('owner')==jam.owner else []
                if d.get('owner')==jam.owner: self.actions.clear()
            return result
        if action=='start': return jam.start(d['owner'])
        if action=='stop': return jam.stop()
        if action=='bars': return jam.bars(d['owner'],d['start'],d.get('count',1))
        if action=='heartbeat': return jam.heartbeat(d['owner'],d['clock'])
        if action=='direction': return jam.direct(d['text'])
        if action=='configure': return jam.configure(d['role'],d.get('controls',{}),d.get('after_bars',0),d.get('muted'))
        if action=='undo': return jam.undo(d['role'])
        if action=='human': return jam.human(d['events'])
        if action=='browser-settings':
            settings=validate_browser(d)
            with jam.lock: jam.session['browser']=settings
            return {'status':'settings saved'}
        if action=='save':
            if 'browser' in d:
                settings=validate_browser(d['browser'])
                with jam.lock: jam.session['browser']=settings
            saved=jam.save()
            if jam.ctx: jam.ctx.state.set('saved_session',saved)
            return saved
        if action=='restore': return jam.restore(d['session'])
        if action=='tempo':
            tempo=number(d['tempo'],40,200)
            with jam.lock:
                if jam.playing: raise ValueError('Stop before changing tempo')
                if jam.session['performance']: raise ValueError('Start a new jam to change tempo after recording')
                jam.session['tempo']=tempo
            return {'tempo':tempo}
        if action=='new':
            from .music import initial_session
            return jam.restore(initial_session())
        if action=='export':
            bars=d.get('bars')
            if bars is None:
                bars=[b for b in jam.save()['performance'] if b['bar']<=jam.clock['bar']]
            if not isinstance(bars,list) or len(bars)>4096: raise ValueError('Invalid performance')
            for bar in bars:
                number(bar['bar'],0,100000); number(bar['tempo'],40,200)
                for role in ROLES: validate_pattern(role,bar['roles'][role]['events'])
                for e in bar.get('human',[]):
                    number(e['pitch'],21,108); number(e['beat'],0,4); number(e['duration'],.04,4); number(e['velocity'],.01,1)
            return {'format':'audio/midi','filename':'agent-music-jam.mid','base64':base64.b64encode(midi(bars,jam.session['browser']['sounds'])).decode()}
        raise ValueError('Unknown action')
