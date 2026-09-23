import copy
import random
import pytest
from game import Match, Fighter, BREEDS, resolve_exchange
from strategy import choose_decision, decision_context, model_signals, empirical_forecast, PERSONAS


def match_with_history(action, n=5):
    m=Match(0, random.Random(21))
    m.history=[dict(round=i+1,player=action,enemy='guard') for i in range(n)]
    m.round=n
    return m


def test_context_is_detached_and_contains_only_closed_rounds():
    m=match_with_history('guard')
    ctx=decision_context(m)
    assert ctx['已结束回合']==5
    assert ctx['玩家最近出招']==['收须固守']*5
    assert 'session' not in str(ctx) and 'action' not in ctx
    m.player.hp=1
    m.history[-1]['player']='attack'
    assert ctx['玩家虫']['耐力']==100
    assert ctx['玩家最近出招'][-1]=='收须固守'


def test_memory_tracks_changed_habits_and_illegal_moves():
    m=match_with_history('guard')
    assert max(empirical_forecast(m),key=empirical_forecast(m).get)=='guard'
    m.history.extend(dict(player='provoke') for _ in range(6))
    assert max(empirical_forecast(m),key=empirical_forecast(m).get)=='provoke'
    m.player.energy=0
    assert empirical_forecast(m)['attack']==0


def test_model_changes_forecast_and_plan_without_fake_confidence():
    m=Match(0,random.Random(5))
    a=choose_decision(m, {'forecast':dict(attack=1,guard=0,provoke=0),'plan':'conserve'})
    b=choose_decision(m, {'forecast':dict(attack=0,guard=0,provoke=1),'plan':'press'})
    assert a['forecast']!=b['forecast'] and a['plan']!=b['plan']
    assert a['source']=='laya' and a['based_on_round']==0
    assert 'confidence' not in a


def test_model_cannot_force_unaffordable_attack():
    m=Match(0,random.Random(3))
    m.player.energy=m.enemy.energy=0
    decision=choose_decision(m,{'forecast':dict(attack=1,guard=0,provoke=0),'plan':'press'})
    assert decision['action']!='attack'
    assert decision['forecast']['attack']==0
    assert 'attack' not in decision['scores']


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1])
def test_invalid_probabilities_are_rejected(bad):
    with pytest.raises(ValueError):
        model_signals({'answers':{'forecast':{'probabilities':dict(attack=bad,guard=0,provoke=1)},'plan':{'choice':'press'}}})


def test_personalities_have_measurably_different_choices():
    choices={key:[] for key in PERSONAS}
    for energy in [20,40,80]:
        for hp in [20,60,100]:
            for history in ['attack','guard','provoke']:
                for key in PERSONAS:
                    m=match_with_history(history)
                    m.persona=key
                    m.enemy.energy=energy
                    m.enemy.hp=hp
                    choices[key].append(choose_decision(m)['action'])
    assert choices['bold']!=choices['patient']
    assert choices['patient']!=choices['reader']


def test_planning_does_not_mutate_fighters_or_history():
    m=match_with_history('attack')
    before=copy.deepcopy(m.state())
    choose_decision(m)
    assert m.state()==before


def test_pure_resolution_is_symmetric_and_uses_pre_turn_spirit():
    a,b=Fighter(BREEDS[0],spirit=59),Fighter(BREEDS[1],spirit=60)
    left,right,_=resolve_exchange(a,b,'provoke','attack')
    reverse_right,reverse_left,_=resolve_exchange(b,a,'attack','provoke')
    assert left==reverse_left and right==reverse_right
    assert a.hp==100 and a.spirit==59


def test_server_passes_no_pending_move_and_reveals_only_after_resolution(monkeypatch):
    import server
    from fastapi.testclient import TestClient
    monkeypatch.setitem(server.MODEL,'status','ready')
    monkeypatch.setattr(server,'inference',None)
    captured=[]
    def fake_predict(context):
        captured.append(copy.deepcopy(context))
        return dict(forecast=dict(attack=0,guard=1,provoke=0),plan='unsettle')
    monkeypatch.setattr(server,'predict',fake_predict)
    monkeypatch.setattr(server,'load_model',lambda: None)
    with TestClient(server.app) as client:
        started=client.post('/api/start',json={'breed':0,'persona':'patient'}).json()
        assert started['decision'] is None and started['review'] is None
        r=client.post('/api/turn',json={'session':started['session'],'action':'provoke'})
        assert r.status_code==200
        assert captured[0]['玩家最近出招']==[]
        decision=r.json()['decision']
        assert decision['actual']=='provoke' and decision['based_on_round']==0
        assert decision['source']=='laya'
        assert client.post('/api/start',json={'breed':0,'persona':'unknown'}).status_code==422


def test_model_judgments_can_change_final_choice_not_only_labels():
    changed=0
    for energy in [20,40,60,80]:
        for persona in PERSONAS:
            m=match_with_history('guard')
            m.persona=persona
            m.enemy.energy=energy
            a=choose_decision(m,dict(forecast=dict(attack=1,guard=0,provoke=0),plan='conserve'))
            b=choose_decision(m,dict(forecast=dict(attack=0,guard=1,provoke=0),plan='unsettle'))
            changed+=a['action']!=b['action']
    assert changed>0


def test_bad_model_falls_back_with_explicit_source(monkeypatch):
    import server
    from fastapi.testclient import TestClient
    monkeypatch.setattr(server,'load_model',lambda: None)
    monkeypatch.setitem(server.MODEL,'status','ready')
    def broken(context): raise ValueError('malformed probabilities')
    monkeypatch.setattr(server,'predict',broken)
    with TestClient(server.app) as c:
        sid=c.post('/api/start',json={'breed':0}).json()['session']
        data=c.post('/api/turn',json={'session':sid,'action':'guard'}).json()
        assert data['decision_source']=='rules'
        assert data['decision']['model_forecast'] is None
        assert '输出不可用' in data['decision']['fallback_reason']
        assert data['round']==1
