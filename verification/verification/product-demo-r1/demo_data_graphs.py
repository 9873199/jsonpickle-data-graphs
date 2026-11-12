"""Separate verification console; all restoration is performed by jsonpickle."""
import json,jsonpickle

def main():
 print('Data Graph Reader\n',flush=True)
 shared={'value':[1,True,None]};root={'left':[shared],'right':shared};root['self']=root
 encoded=jsonpickle.encode(root);print('Stored JSON graph: '+encoded,flush=True)
 value=jsonpickle.decode(encoded,data_only=True)
 shared_ok=value['left'][0] is value['right'];cycle_ok=value['self'] is value
 print('Shared dictionary identity: '+str(shared_ok),flush=True);print('Self reference: '+str(cycle_ok),flush=True)
 checks=[shared_ok,cycle_ok]
 for label,payload in [('Object marker',{'nested':{'py/object':'builtins.str'}}),('Boolean reference number',[{'py/id':True}]),('Out-of-range reference',[{'py/id':999}])]:
  print('\n'+label+': '+json.dumps(payload),flush=True)
  try:
   result=jsonpickle.decode(json.dumps(payload),data_only=True);print('Accepted: '+repr(result),flush=True);checks.append(False)
  except ValueError as error:print('Rejected: '+str(error),flush=True);checks.append(True)
 legacy=jsonpickle.decode(jsonpickle.encode((1,2)));checks.append(legacy==(1,2));print('\nDefault tuple compatibility: '+repr(legacy),flush=True)
 print(json.dumps({'checks':len(checks),'passed':sum(checks),'source':'actual library calls; separate verification helper'}),flush=True)
 return 0 if all(checks) else 1
if __name__=='__main__':raise SystemExit(main())
