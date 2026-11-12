import json,jsonpickle
from jsonpickle.unpickler import Unpickler
class Counted:
 events=[]
 def __new__(cls,*a,**k):cls.events.append('__new__');return super().__new__(cls)
 def __setstate__(self,state):self.events.append('__setstate__');self.state=state
print('Data reader context checks - separate verification helper',flush=True)
payload=json.dumps({'py/object':'harmless.Counted','py/state':{'value':7}})
print('Input: '+payload,flush=True)
ok=True
for label,kwargs in [('Default context',{}),('Existing ordinary context',{'context':Unpickler()})]:
 Counted.events=[];print('\n'+label,flush=True)
 try:
  value=jsonpickle.decode(payload,data_only=True,classes={'harmless.Counted':Counted},**kwargs)
  print('Restored type: '+type(value).__name__,flush=True);ok=False
 except ValueError as error:print('Rejected: '+str(error),flush=True)
 print('Harmless restoration hooks: '+repr(Counted.events),flush=True)
value=Unpickler(data_only=True).restore((1,2));print('\nDirect restore tuple result: '+repr(value),flush=True)
if type(value) is tuple:ok=False
raise SystemExit(0 if ok else 1)
