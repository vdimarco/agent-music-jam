"""Pure musical data, validation and standard MIDI export. No audio or model work."""
import copy
import math
import struct

ROLES = ('drums', 'bass', 'keys', 'lead')
RANGES = {'drums': (35, 51), 'bass': (28, 60), 'keys': (48, 88), 'lead': (55, 96)}
CHORDS = [(50, 53, 57, 60, 64), (43, 46, 50, 53, 57), (46, 50, 53, 57, 60), (45, 49, 52, 55, 58)]
CONTROLS = {'density': .55, 'energy': .55, 'complexity': .35, 'register': 0, 'swing': .12, 'variation': .25}

def number(v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f'Expected finite number from {lo} to {hi}')
    return v

def controls(data):
    if not isinstance(data, dict) or set(data) - set(CONTROLS):
        raise ValueError('Unknown musician control')
    return {k: number(v, -12 if k == 'register' else 0, 12 if k == 'register' else 1) for k, v in data.items()}

def validate_pattern(role, events):
    if role not in ROLES or not isinstance(events, list) or len(events) > 256:
        raise ValueError('Invalid role or oversized pattern')
    clean = []
    for e in events:
        if not isinstance(e, dict): raise ValueError('Event must be an object')
        bar, beat = number(e.get('bar'), 0, 3), number(e.get('beat'), 0, 3.999)
        pitch = number(e.get('pitch'), *RANGES[role])
        duration = number(e.get('duration'), .04, 4)
        velocity = number(e.get('velocity'), .01, 1)
        if bar != int(bar) or pitch != int(pitch) or beat + duration > 4.001:
            raise ValueError('Events must fit their bar, with integer MIDI pitches')
        if role == 'drums' and pitch not in (36, 38, 42, 46, 49): raise ValueError('Unsupported drum')
        articulation = e.get('articulation', 'normal')
        if articulation not in ('normal', 'staccato', 'accent'): raise ValueError('Unsupported articulation')
        clean.append(dict(bar=int(bar), beat=beat, pitch=int(pitch), duration=duration,
                          velocity=velocity, instrument=role, articulation=articulation))
    for bar in range(4):
        points = sorted((e['beat'] + end * e['duration'], -1 if end else 1)
                        for e in clean if e['bar'] == bar for end in (0, 1))
        voices = 0
        for _, delta in points:
            voices += delta
            if voices > {'drums': 5, 'bass': 1, 'keys': 6, 'lead': 1}[role]:
                raise ValueError('Polyphony limit exceeded')
    return sorted(clean, key=lambda e: (e['bar'], e['beat'], e['pitch']))

def pattern(role, c, motif=None):
    out = []
    def add(bar, beat, pitch, duration, velocity):
        shift = round(c['register']) if role != 'drums' else 0
        pitch = max(RANGES[role][0], min(RANGES[role][1], pitch + shift))
        if beat % 1 == .5: beat += c['swing'] * .25
        duration = min(duration, 4-beat)
        out.append(dict(bar=bar, beat=beat, pitch=pitch, duration=duration,
                        velocity=min(.94, velocity * (.55+c['energy']*.6)), articulation='normal'))
    for bar, chord in enumerate(CHORDS):
        root = chord[0]
        if role == 'drums':
            for beat in (0, 2): add(bar, beat, 36, .14, .85)
            for beat in (1, 3): add(bar, beat, 38, .12, .66)
            for i in range(8 if c['density'] > .35 else 4):
                add(bar, i*(.5 if c['density'] > .35 else 1), 42, .06, .32 if i%2 else .48)
            if c['complexity'] > .65 and bar == 3:
                for beat in (3.25, 3.5, 3.75): add(bar, beat, 38, .08, .42)
        elif role == 'bass':
            add(bar, 0, root-12, .85, .8)
            add(bar, 2, root-12, .7, .65)
            if c['density'] > .45: add(bar, 1.5, root-5, .3, .55)
            if c['density'] > .7: add(bar, 3.5, CHORDS[(bar+1)%4][0]-13, .3, .5)
        elif role == 'keys':
            for beat in ([.5, 2.5] if c['density'] > .4 else [.5]):
                for p in chord[1:]: add(bar, beat, p+12, 1.05 if c['energy'] < .7 else .5, .34)
        elif role == 'lead' and c['density'] > .05:
            notes = motif or [69, 72, 76, 74]
            for i, beat in enumerate([.5, 1.5, 2.5] if c['density'] > .65 else [.5, 2]):
                if bar % 2 == 0 or c['variation'] > .6:
                    add(bar, beat, notes[(bar+i)%len(notes)], .42, .43)
    if role in ('bass', 'lead'):
        ordered = sorted(out, key=lambda e: (e['bar'], e['beat']))
        for event, following in zip(ordered, ordered[1:]):
            if event['bar'] == following['bar']:
                event['duration'] = min(event['duration'], following['beat'] - event['beat'])
    return validate_pattern(role, out)

def initial_session():
    intentions = ['A dry backbeat. Let the pocket breathe.', 'Rooted, warm, locked to the kick.', 'Soft ninths, with air between chords.', 'A small motif. Then a little silence.']
    return dict(version=1, tempo=92, key='D minor', meter=4, progression=['Dm9','Gm9','Bbmaj7','A7'],
                browser={'sounds':{'keys':{'instrument':'electric','tone':.5},'human':{'instrument':'piano','tone':.5}},'mix':{r:{'volume':.65 if r=='human' else .7,'mute':False,'solo':False} for r in (*ROLES,'human')}},
                roles={r: dict(controls=copy.deepcopy(CONTROLS), pattern=pattern(r, CONTROLS),
                               motif=[69,72,76,74], intention=intentions[i], muted=False)
                       for i,r in enumerate(ROLES)}, arrangement=[], history={r: [] for r in ROLES}, pending=[], performance=[], next_bar=0)

def validate_browser(data):
    if not isinstance(data,dict): raise ValueError('Invalid browser settings')
    result={'sounds':{},'mix':{}}
    data={**data,'sounds':data.get('sounds',{'keys':{'instrument':'electric','tone':.5},'human':{'instrument':'piano','tone':.5}})}
    for role in ('keys','human'):
        sound=data['sounds'][role]
        if sound['instrument'] not in ('piano','electric','organ','pad','pluck'): raise ValueError('Unknown instrument')
        result['sounds'][role]={'instrument':sound['instrument'],'tone':number(sound['tone'],0,1)}
    for role in (*ROLES,'human'):
        mix=data['mix'][role]
        if not isinstance(mix['mute'],bool) or not isinstance(mix['solo'],bool): raise ValueError('Invalid mixer flags')
        result['mix'][role]={'volume':number(mix['volume'],0,1),'mute':mix['mute'],'solo':mix['solo']}
    return result

def validate_session(s):
    if not isinstance(s, dict) or s.get('version') != 1: raise ValueError('Unsupported session version')
    number(s.get('tempo'), 40, 200)
    if s.get('key') != 'D minor' or s.get('meter') != 4: raise ValueError('This ensemble supports D minor in 4/4')
    def role_state(r, state):
        if not isinstance(state, dict): raise ValueError('Invalid role state')
        state['controls'] = {**CONTROLS, **controls(state.get('controls', {}))}
        state['pattern'] = validate_pattern(r, state.get('pattern'))
        if not isinstance(state.get('intention'), str) or len(state['intention']) > 240: raise ValueError('Invalid intention')
        if not isinstance(state.get('muted'), bool): raise ValueError('Invalid mute state')
        motif = state.get('motif')
        if not isinstance(motif, list) or not 1 <= len(motif) <= 32: raise ValueError('Invalid motif')
        for n in motif: number(n, 28, 96)
    s = copy.deepcopy(s)
    s['browser']=validate_browser(s.get('browser',initial_session()['browser']))
    if set(s.get('roles', {})) != set(ROLES): raise ValueError('Four musicians required')
    for r in ROLES:
        role_state(r, s['roles'][r])
        if len(s.get('history', {}).get(r, [])) > 64: raise ValueError('History too long')
        for item in s['history'][r]: role_state(r, item)
    if len(s.get('pending', [])) > 64 or len(s.get('performance', [])) > 4096: raise ValueError('Session too large')
    for change in s.get('pending', []):
        if change['role'] not in ROLES: raise ValueError('Invalid arrangement role')
        role_state(change['role'], change['state'])
        number(change['earliest'], 0, 100000)
    frontier=number(s.get('next_bar'), 0, 100000)
    if frontier != int(frontier): raise ValueError('Whole bar frontier required')
    if s.get('progression') != ['Dm9','Gm9','Bbmaj7','A7']: raise ValueError('Unsupported progression')
    if not isinstance(s.get('arrangement'), list) or len(s['arrangement']) > 4096: raise ValueError('Invalid arrangement')
    for bar in s['performance']:
        number(bar['bar'], 0, 100000)
        number(bar['tempo'], 40, 200)
        for r in ROLES:
            validate_pattern(r, bar['roles'][r]['events'])
    return s

def vlq(n):
    values = [n & 127]
    while n >> 7:
        n >>= 7
        values.insert(0, (n & 127) | 128)
    return bytes(values)

def midi(bars, sounds=None):
    sounds = sounds or {}
    tracks = []
    tempo = bars[0]['tempo'] if bars else 92
    meta = b'\0\xff\x51\x03' + int(60_000_000/tempo).to_bytes(3,'big') + b'\0\xff\x58\x04\x04\x02\x18\x08\0\xff\x2f\0'
    tracks.append(meta)
    origin = bars[0]['bar'] if bars else 0
    for role, channel, program in [('drums',9,0),('bass',0,33),('keys',1,4),('lead',2,80),('human',3,4)]:
        if role in sounds:
            program = {'piano':0,'electric':4,'organ':16,'pad':89,'pluck':10}[sounds[role]['instrument']]
        events = []
        for bar in bars:
            notes = bar.get('human', []) if role == 'human' else bar['roles'][role]['events']
            for e in notes:
                tick = round(((bar['bar']-origin)*4+e['beat'])*480)
                length = max(1, round(e['duration']*480))
                events.extend([(tick, 1, bytes([0x90+channel,e['pitch'],round(e['velocity']*127)])),
                               (tick+length, 0, bytes([0x80+channel,e['pitch'],0]))])
        name = role.encode()
        body = b'\0\xff\x03'+vlq(len(name))+name+b'\0'+bytes([0xc0+channel,program])
        previous = 0
        for tick, _, data in sorted(events):
            body += vlq(tick-previous)+data
            previous = tick
        body += b'\0'+bytes([0xb0+channel,64,0])+b'\0'+bytes([0xb0+channel,123,0])+b'\0\xff\x2f\0'
        tracks.append(body)
    return b'MThd'+struct.pack('>IHHH',6,1,len(tracks),480)+b''.join(b'MTrk'+struct.pack('>I',len(t))+t for t in tracks)
