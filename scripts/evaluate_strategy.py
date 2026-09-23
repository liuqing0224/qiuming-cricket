"""Reproducible small policy diagnostic, not a claim about human win rates.
Run from repository root: python scripts/evaluate_strategy.py
No model weights needed. Compares the fallback policy with the v1 random baseline.
"""
import json
from pathlib import Path
import random
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game import Match
from strategy import PERSONAS, choose_decision


def human_move(match, kind):
    if match.player.energy < 18: return 'guard'
    if kind == 'attack': return 'attack'
    if kind == 'guard': return 'attack' if match.round % 4 == 3 else 'guard'
    if kind == 'provoke': return 'attack' if match.round % 3 == 2 else 'provoke'
    return ['attack','guard','provoke'][match.round % 3]


def evaluate(seeds=40):
    report=[]
    for persona in PERSONAS:
        for policy in ['v1-random','adaptive-rules']:
            summary=dict(persona=persona,policy=policy,games=0,enemy_wins=0,draws=0,enemy_losses=0,moves=dict(attack=0,guard=0,provoke=0))
            for kind in ['attack','guard','provoke','cycle']:
                for seed in range(seeds):
                    match=Match(seed%3,random.Random(seed),persona=persona)
                    while not match.result:
                        move=match.fallback() if policy=='v1-random' else choose_decision(match)['action']
                        summary['moves'][move]+=1
                        match.step(human_move(match,kind),move)
                    summary['games']+=1
                    key={'lose':'enemy_wins','win':'enemy_losses','draw':'draws'}[match.result]
                    summary[key]+=1
            report.append(summary)
    return report

if __name__=='__main__':
    print(json.dumps(dict(note='Four scripted opponents, 40 seeds each. No Laya inference; validates the strategic fallback only.',results=evaluate()),ensure_ascii=False,indent=2))
