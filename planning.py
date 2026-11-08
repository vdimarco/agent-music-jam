"""Conductor plus role-scoped planners; Hermes owns every model credential."""
import json
import re
from .music import ROLES, controls, pattern, validate_pattern

CONTROL_SCHEMA = {'type':'object','properties':{k:{'type':'number'} for k in ('density','energy','complexity','register','swing','variation')},'additionalProperties':False}
CHANGE_SCHEMA = {'type':'object','properties':{'role':{'type':'string','enum':list(ROLES)},'controls':CONTROL_SCHEMA,'muted':{'type':'boolean'},'intention':{'type':'string'},'after_bars':{'type':'integer','minimum':0,'maximum':64}},'required':['role','controls','muted','intention','after_bars'],'additionalProperties':False}
DIRECTION_SCHEMA = {'type':'object','properties':{'changes':{'type':'array','items':CHANGE_SCHEMA,'maxItems':8}},'required':['changes'],'additionalProperties':False}
EVENT_SCHEMA = {'type':'object','properties':{'bar':{'type':'integer'},'beat':{'type':'number'},'pitch':{'type':'integer'},'duration':{'type':'number'},'velocity':{'type':'number'},'articulation':{'type':'string','enum':['normal','staccato','accent']}},'required':['bar','beat','pitch','duration','velocity','articulation'],'additionalProperties':False}
PATTERN_SCHEMA = {'type':'object','properties':{'events':{'type':'array','items':EVENT_SCHEMA,'maxItems':256}},'required':['events'],'additionalProperties':False}

class Planner:
    def __init__(self, ctx=None): self.ctx = ctx

    def structured(self, instructions, data, schema, purpose):
        result = self.ctx.llm.complete_structured(instructions=instructions,
            input=[{'type':'text','text':json.dumps(data)}],json_schema=schema,
            purpose=purpose, max_tokens=5000, timeout=40)
        if result.parsed is None: raise ValueError('Model returned no valid structured plan')
        return result.parsed

    def conduct(self, text, session):
        if self.ctx:
            return self.structured('You conduct a restrained D minor 4/4 soul ensemble. Interpret the direction into changes ONLY for affected musicians. Controls are 0..1 except register -12..12 semitones. after_bars is delay from next available bar. Keep unaffected controls unchanged. For a temporary solo, mute lead and thin keys, then schedule their return after four bars. For a fill raise drums complexity, then restore after one bar. Never include credentials or unrelated data.',
                {'direction':text, 'roles':session['roles'], 'progression':session['progression']}, DIRECTION_SCHEMA, 'jam.conductor')['changes']
        # Standalone mode has a deliberately small, explicit command vocabulary.
        low = text.lower()
        roles = [r for r in ROLES if r in low or (r == 'bass' and 'bassist' in low) or (r == 'drums' and 'drummer' in low)]
        if 'solo' in low or 'breakdown' in low:
            return [dict(role=r, controls={'density':.15}, muted=r=='lead', intention='Space for your phrase.',after_bars=0) for r in ('keys','lead')]+[dict(role=r, controls=session['roles'][r]['controls'],muted=False,intention='Back in the conversation.',after_bars=4) for r in ('keys','lead')]
        if not roles: raise ValueError('Standalone directions: name drums, bass, keys or lead; ask for less busy, more energy, darker, a fill, or space for a solo. Free-form planning needs Hermes.')
        changes=[]
        for role in roles:
            c={}
            if any(x in low for x in ('less','space','simpler')): c['density']=.2; c['complexity']=.15
            if any(x in low for x in ('busier','more energy','build')): c['density']=.8; c['energy']=.75
            if 'darker' in low: c['register']=-5; c['energy']=.35
            if 'fill' in low: c['complexity']=.85
            if 'swing' in low: c['swing']=.65
            if 'answer' in low: c['variation']=.8
            if not c and not any(x in low for x in ('mute','back','return')): raise ValueError('Direction needs Hermes, or use less busy / darker / fill / more energy / answer.')
            delay=4 if 'after four' in low or 'after 4' in low else 0
            changes.append(dict(role=role,controls=c,muted='mute' in low,intention=text[:180],after_bars=delay))
            if 'fill' in low: changes.append(dict(role=role,controls=session['roles'][role]['controls'],muted=False,intention='Return to the pocket.',after_bars=1))
        return changes

    def musician(self, role, state, session, phrase, lifecycle=None):
        prompt = ('Compose exactly one four-bar pattern as JSON {"events":[{bar,beat,pitch,duration,velocity,articulation}]}. '
                  'bar 0..3, beat 0..<4, duration .04..4 ending inside bar, velocity .01..1. '
                  'articulation normal/staccato/accent. Groove and repetition matter; leave space. '
                  'MIDI ranges drums 35..51 (only 36,38,42,46,49), bass 28..60 monophonic, keys 48..88 up to six voices, lead 55..96 monophonic. '
                  'Use progression Dm9 Gm9 Bbmaj7 A7, one chord per bar. Preserve the motif and develop it subtly. '
                  'Respond to the human phrase if supplied. Return only JSON, no tools.')
        data=dict(role=role,state=state,ensemble={r:s['intention'] for r,s in session['roles'].items()},human_phrase=phrase)
        if lifecycle:
            handle = lifecycle.launch({'goal':prompt, 'context':json.dumps(data), 'role':'leaf', 'allowed_toolsets':[]})
            outcome=lifecycle.wait(handle,timeout_seconds=45)
            if outcome.timed_out:
                lifecycle.cancel(handle,reason='Composition deadline; previous pattern continues')
                raise TimeoutError('Musician exceeded planning deadline')
            result=lifecycle.result(handle)
            payload=result.structured_payload or json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', result.summary or '').strip())
            return validate_pattern(role,payload['events'])
        if self.ctx:
            return validate_pattern(role,self.structured(prompt,data,PATTERN_SCHEMA,'jam.musician.'+role)['events'])
        motif = state['motif']
        if phrase:
            motif=[max(28 if role=='bass' else 55,min(60 if role=='bass' else 96,e['pitch']-(24 if role=='bass' else 0))) for e in phrase[-8:]]
            state['motif']=motif
        return pattern(role, state['controls'], motif)
