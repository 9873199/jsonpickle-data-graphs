"""Security-mode entry consistency with caller-provided restoration contexts."""
import json,pytest,jsonpickle
from jsonpickle.unpickler import Unpickler

@pytest.mark.parametrize('payload',[{'nested':{'py/object':'builtins.str'}},{'nested':{'py/reduce':[{'py/function':'builtins.str'},['value']]}}])
def test_decode_data_only_cannot_be_disabled_by_legacy_context(payload,monkeypatch):
 import jsonpickle.unpickler as module
 calls=[]
 def forbidden(*args,**kwargs):calls.append('legacy_restore');raise AssertionError('legacy restoration branch reached')
 monkeypatch.setattr(module.util,'loadclass',forbidden)
 monkeypatch.setattr(Unpickler,'_restore_object',forbidden)
 monkeypatch.setattr(Unpickler,'_restore_reduce',forbidden)
 context=Unpickler()
 with pytest.raises(ValueError):jsonpickle.decode(json.dumps(payload),context=context,data_only=True)
 assert calls==[]

@pytest.mark.parametrize('value',[(1,2),{1:'non-string-key'}])
def test_direct_data_only_restore_accepts_only_documented_json_shapes(value):
 with pytest.raises(ValueError):Unpickler(data_only=True).restore(value)

def test_root_reference_cannot_resolve_a_missing_container():
 with pytest.raises(ValueError):jsonpickle.decode('{"py/id":0}',data_only=True)
