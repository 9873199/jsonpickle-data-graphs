import json
import pytest
import jsonpickle
from jsonpickle.unpickler import Unpickler

def test_plain_json_business_keys_preserved():
 value={'name':'sample','meta':{'pythonic':'text','json_value':3},'flags':[True,None,2.5]}
 assert jsonpickle.decode(json.dumps(value),data_only=True)==value
 assert jsonpickle.loads(json.dumps(value),data_only=True)==value

def test_shared_dictionary_identity_preserved():
 shared={'value':1};value=[shared,shared];out=jsonpickle.decode(jsonpickle.encode(value),data_only=True);assert out[0] is out[1] and out[0]==shared
def test_list_self_cycle():
 x=[];x.append(x);out=jsonpickle.decode(jsonpickle.encode(x),data_only=True);assert out[0] is out
def test_dictionary_self_cycle():
 x={};x['self']=x;out=jsonpickle.decode(jsonpickle.encode(x),data_only=True);assert out['self'] is out
def test_mutual_list_dictionary_cycle():
 x=[];d={'back':x};x.append(d);out=jsonpickle.decode(jsonpickle.encode(x),data_only=True);assert out[0]['back'] is out
@pytest.mark.parametrize('marker',['py/object','py/type','py/function','py/reduce','py/repr','py/mod','py/state','py/newargs','py/tuple','py/set','py/unknown'])
def test_object_markers_refused_before_legacy_hooks(marker,monkeypatch):
 calls=[]
 def forbidden(*a,**k):calls.append('legacy');raise AssertionError('legacy restoration reached')
 import jsonpickle.unpickler as module
 monkeypatch.setattr(module.util,'loadclass',forbidden)
 if hasattr(module,'loadclass'):monkeypatch.setattr(module,'loadclass',forbidden)
 for method in ['_restore_object','_restore_reduce','_restore_repr']:
  if hasattr(Unpickler,method):monkeypatch.setattr(Unpickler,method,forbidden)
 with pytest.raises(ValueError):jsonpickle.decode(json.dumps({'nested':[{marker:'builtins.str'}]}),data_only=True)
 assert calls==[]
@pytest.mark.parametrize('bad_id',[-1,True,False,999,'0',None,1.0])
def test_invalid_references_rejected(bad_id):
 with pytest.raises(ValueError):jsonpickle.decode(json.dumps([{'py/id':bad_id}]),data_only=True)
def test_encoded_keys_cannot_hide_restore_markers():
 key='json://'+json.dumps({'py/object':'builtins.str'})
 with pytest.raises(ValueError):jsonpickle.decode(json.dumps({key:'value'}),keys=True,data_only=True)
def test_direct_unpickler_entry_and_failure_reset():
 context=Unpickler(data_only=True)
 assert context.restore({'plain':[1,2]})=={'plain':[1,2]}
 with pytest.raises(ValueError):context.restore({'nested':{'py/object':'builtins.str'}})
 assert context.restore({'plain':3})=={'plain':3}
def test_classes_argument_does_not_authorize_object_restore():
 with pytest.raises(ValueError):jsonpickle.decode('{"py/object":"builtins.str"}',classes={'builtins.str':str},data_only=True)
def test_legacy_default_retains_object_support():
 assert jsonpickle.decode(jsonpickle.encode((1,2)))==(1,2)

def test_mixed_topology_retains_legacy_reference_numbering():
 shared={'value':[1,True,None]};root={'left':[shared],'right':shared};root['self']=root
 encoded=jsonpickle.encode(root)
 value=jsonpickle.decode(encoded,data_only=True)
 assert value['left'][0] is value['right'] and value['self'] is value
 assert value['right']['value']==[1,True,None]

@pytest.mark.parametrize('marker',['py/b64','py/b85','py/bytes','py/bytea','py/memoryview','py/iterator','py/initargs','py/newargsex','py/newobj','py/property','py/default_factory','py/ref','py/seq'])
def test_all_other_reserved_marker_families_rejected(marker):
 with pytest.raises(ValueError):jsonpickle.decode(json.dumps({'deep':{marker:[]}}),data_only=True)

def test_registered_handler_cannot_restore_in_data_only_mode():
 from jsonpickle import handlers,util
 calls=[]
 class BusinessObject:pass
 class CountingHandler(handlers.BaseHandler):
  def restore(self,data):calls.append('restore');return BusinessObject()
 handlers.register(BusinessObject,CountingHandler)
 try:
  payload=json.dumps({'py/object':util.importable_name(BusinessObject)})
  with pytest.raises(ValueError):jsonpickle.decode(payload,classes={util.importable_name(BusinessObject):BusinessObject},data_only=True)
  assert calls==[]
 finally:handlers.unregister(BusinessObject)
