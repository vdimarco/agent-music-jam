import copy
import importlib.util
import json
from pathlib import Path
import struct
import sys
import threading
import time
import unittest
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('agent_music_jam',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
from agent_music_jam.engine import Jam
from agent_music_jam.music import validate_browser, ROLES, initial_session, validate_pattern, validate_session, midi, pattern, CONTROLS
from agent_music_jam.server import Service

class MusicTests(unittest.TestCase):
    def test_ensemble_and_extreme_controls(self):
        for r in ROLES:
            for level in (0,.5,1):
                c={**CONTROLS,**{k:level for k in CONTROLS if k!='register'}}
                for shift in (-12,0,12):
                    c['register']=shift
                    validate_pattern(r,pattern(r,c))
    def test_reject_malformed_events(self):
        e=initial_session()['roles']['bass']['pattern'][0]
        for patch in ({'beat':float('nan')},{'pitch':999},{'duration':-1},{'articulation':'script'},{'bar':.5}):
            with self.assertRaises(ValueError): validate_pattern('bass',[{**e,**patch}])
        with self.assertRaises(ValueError): validate_pattern('bass',[e,e])
    def test_selective_undo(self):
        jam=Jam(); before=jam.save()['roles'];jam.start('test');jam.bars('test',0,3)
        jam.configure('bass',{'density':.1});bar=jam.bars('test',3)["bars"][0]
        self.assertNotEqual(jam.save()['roles']['bass'],before['bass'])
        for r in ('drums','keys','lead'): self.assertEqual(before[r],jam.save()['roles'][r])
        jam.undo('bass');jam.bars('test',4)
        self.assertEqual(before['bass'],jam.save()['roles']['bass'])
    def test_slow_model_fallback_and_actual_boundary(self):
        jam=Jam(); gate=threading.Event();original=jam.planner.conduct
        def delayed(text,s): gate.wait(3);return original(text,s)
        jam.planner.conduct=delayed;jam.start('test');jam.direct('Make drums less busy')
        bars=jam.bars('test',0,4)['bars'];self.assertEqual(len(bars),4);self.assertEqual(jam.status()['jobs'][0]['status'],'planning')
        gate.set();self.wait_done(jam)
        jam.bars('test',4)
        job=jam.status()['jobs'][0];self.assertEqual(job['activations'],[{'role':'drums','bar':5}])
    def wait_done(self,jam):
        end=time.monotonic()+4
        while any(j['status']=='planning' for j in jam.status()['jobs']):
            if time.monotonic()>end: self.fail('Planner timed out')
            time.sleep(.01)
    def test_stopped_planner_cannot_commit(self):
        jam=Jam();gate=threading.Event();original=jam.planner.conduct
        def delayed(text,s):gate.wait(3);return original(text,s)
        jam.planner.conduct=delayed;jam.direct('Make drums less busy');jam.stop();gate.set();time.sleep(.05)
        self.assertEqual(jam.session['pending'],[])
    def test_arrangement_returns_after_four_bars(self):
        jam=Jam();jam.start('test');jam.direct('Leave space for my solo');self.wait_done(jam)
        jam.bars('test',0,4);self.assertTrue(jam.session['roles']['lead']['muted'])
        jam.bars('test',4);self.assertFalse(jam.session['roles']['lead']['muted'])
    def test_restore_atomic_and_complete(self):
        jam=Jam();jam.configure('bass',{'density':.2},4);saved=jam.save();jam.restore(saved)
        self.assertEqual(jam.save(),saved);self.assertFalse(jam.playing)
        bad=copy.deepcopy(saved);bad['roles']['bass']['pattern'][0]['pitch']=999
        with self.assertRaises(ValueError):jam.restore(bad)
        self.assertEqual(jam.save(),saved)
    def test_owner_and_frontier(self):
        jam=Jam();jam.start('a')
        with self.assertRaises(ValueError):jam.start('b')
        with self.assertRaises(ValueError):jam.bars('b',0)
        jam.bars('a',0)
        with self.assertRaises(ValueError):jam.bars('a',0)
    def test_midi_chunks_and_events(self):
        jam=Jam();jam.start('test');bars=jam.bars('test',0,4)['bars'];data=midi(bars)
        self.assertEqual(data[:4],b'MThd');self.assertEqual(struct.unpack('>HHH',data[8:14]),(1,6,480))
        offset=14;tracks=[]
        while offset<len(data):
            self.assertEqual(data[offset:offset+4],b'MTrk');size=int.from_bytes(data[offset+4:offset+8],'big');track=data[offset+8:offset+8+size];self.assertTrue(track.endswith(b'\xff\x2f\0'));tracks.append(track);offset+=8+size
        self.assertEqual(len(tracks),6);self.assertEqual(offset,len(data))
    def test_sound_settings_round_trip(self):
        jam=Jam();session=jam.save();session['browser']['sounds']['human']={'instrument':'organ','tone':.9};jam.restore(session)
        self.assertEqual(jam.save()['browser']['sounds']['human'],{'instrument':'organ','tone':.9})
        bad=copy.deepcopy(session);bad['browser']['sounds']['human']['instrument']='remote-url'
        with self.assertRaises(ValueError): jam.restore(bad)
        self.assertEqual(jam.save(),session)

    def test_repeated_undo_walks_backwards(self):
        jam=Jam();jam.start('test');original=jam.save()['roles']['bass']
        jam.configure('bass',{'density':.2});jam.bars('test',0);first=copy.deepcopy(jam.session['roles']['bass'])
        jam.configure('bass',{'density':.8});jam.bars('test',1);jam.undo('bass');jam.bars('test',2)
        self.assertEqual(jam.session['roles']['bass'],first)
        jam.undo('bass');jam.bars('test',3);self.assertEqual(jam.session['roles']['bass'],original)

    def test_human_phrase(self):
        jam=Jam();jam.start('test');jam.bars('test',0);jam.human([{'pitch':72,'bar':0,'beat':1,'duration':.5,'velocity':.7}]);self.assertEqual(jam.phrase[0]['pitch'],72)
        jam.direct('Have bass answer my melody');self.wait_done(jam);jam.bars('test',1)
        self.assertEqual(jam.session['roles']['bass']['motif'],[48])

class ServiceTests(unittest.TestCase):
    def setUp(self):self.s=Service()
    def tearDown(self):self.s.close()
    def request(self,token=None,origin=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        if origin:headers['Origin']=origin
        return urllib.request.urlopen(urllib.request.Request(self.s.origin+'/api/status',b'{}',headers))
    def test_auth_and_origin(self):
        for token,origin,code in [(None,None,401),('bad',None,401),(self.s.token,'https://evil.invalid',403)]:
            with self.assertRaises(urllib.error.HTTPError) as c:self.request(token,origin)
            self.assertEqual(c.exception.code,code);c.exception.close()
        with self.request(self.s.token,self.s.origin) as response:self.assertEqual(response.status,200)
    def test_static_and_no_secret_in_save(self):
        with urllib.request.urlopen(self.s.origin+'/') as response:self.assertEqual(response.status,200)
        self.assertNotIn(self.s.token,json.dumps(self.s.jam.save()))
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.s.origin+'/../engine.py')
        error.exception.close()

if __name__=='__main__':unittest.main()
