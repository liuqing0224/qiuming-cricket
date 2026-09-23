import random
import pytest
from game import Match


def test_guard_mitigates_attack():
    attack, guard = Match(0, random.Random(4)), Match(0, random.Random(4))
    attack.step('provoke','attack')
    guard.step('guard','attack')
    assert guard.player.hp > attack.player.hp
    assert guard.player.energy == 100


def test_exhaustion_rejects_without_advancing():
    m = Match(0)
    m.player.energy = 17
    with pytest.raises(ValueError): m.step('attack','guard')
    assert m.round == 0


def test_provoke_punishes_guard():
    m = Match(0)
    m.step('provoke','guard')
    assert m.player.spirit == 69
    assert m.enemy.spirit == 38


def test_stalemate_ends_in_twenty_rounds():
    m = Match(0)
    for _ in range(20): m.step('guard','guard')
    assert m.result == 'draw'
    with pytest.raises(ValueError): m.step('attack','attack')


def test_many_matches_terminate_with_bounded_stats():
    for seed in range(100):
        rng = random.Random(seed)
        m = Match(seed%3,rng)
        while not m.result:
            action = rng.choice(['attack','guard','provoke']) if m.player.energy >= 18 else 'guard'
            m.step(action,m.fallback())
            for f in [m.player,m.enemy]:
                assert all(0<=x<=100 for x in [f.hp,f.energy,f.spirit])
        assert m.round<=20


def test_api_contract(monkeypatch):
    monkeypatch.setenv('LAYA_DISABLE','1')
    from fastapi.testclient import TestClient
    import server
    with TestClient(server.app) as c:
        assert c.post('/api/start',json={'breed':4}).status_code == 422
        s=c.post('/api/start',json={'breed':1}).json()['session']
        assert c.post('/api/turn',json={'session':s,'action':'cheat'}).status_code==422
        for _ in range(20):
            r=c.post('/api/turn',json={'session':s,'action':'guard'})
            assert r.status_code==200
            if r.json()['result']:break
        assert r.json()['result']
        assert c.post('/api/turn',json={'session':s,'action':'guard'}).status_code==409
        assert c.get('/').status_code==200
