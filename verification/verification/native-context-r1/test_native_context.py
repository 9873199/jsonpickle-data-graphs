import json,pytest,jsonpickle
from jsonpickle.unpickler import Unpickler
class Counted:
 events=[]
 def __new__(cls,*a,**k):cls.events.append('__new__');return super().__new__(cls)
 def __setstate__(self,state):self.events.append('__setstate__');self.state=state
@pytest.mark.parametrize('entry',[jsonpickle.decode,jsonpickle.loads])
@pytest.mark.parametrize('legacy_context',[False,True])
def test_real_class_hooks_are_not_called(entry,legacy_context):
 Counted.events=[]
 payload=json.dumps({'py/object':'harmless.Counted','py/state':{'value':7}})
 kwargs={'data_only':True,'classes':{'harmless.Counted':Counted}}
 if legacy_context:kwargs['context']=Unpickler()
 rejected=False
 try:
  result=entry(payload,**kwargs)
  print('RESULT',type(result).__name__,'EVENTS',Counted.events)
 except ValueError:
  rejected=True;print('REJECTED','EVENTS',Counted.events)
 assert rejected and Counted.events==[]
