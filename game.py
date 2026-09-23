"""Authoritative, simultaneous cricket combat. All numbers are game design, not biology."""
from dataclasses import dataclass, asdict
import random

BREEDS = [
    dict(id='qing', name='青背将军', title='均衡型', attack=17, defense=8, speed=7, color='#526652', description='青背金翅，沉稳善战。攻守兼备，适合初入虫场。'),
    dict(id='zi', name='紫衣侯', title='强攻型', attack=22, defense=4, speed=6, color='#766077', description='紫头阔颚，性烈如火。出手凌厉，须留意体力。'),
    dict(id='jin', name='金翅郎', title='灵巧型', attack=15, defense=6, speed=12, color='#b68a45', description='金翅长足，轻捷灵动。善于闪避，伺机反击。'),
]
ACTIONS = {'attack': '振翅强攻', 'guard': '收须固守', 'provoke': '执草挑逗'}

@dataclass
class Fighter:
    breed: dict
    hp: int = 100
    energy: int = 80
    spirit: int = 50
    def data(self): return asdict(self)

class Match:
    def __init__(self, breed, rng=None):
        self.rng = rng or random.Random()
        self.player = Fighter(BREEDS[breed].copy())
        self.enemy = Fighter(self.rng.choice([b for b in BREEDS if b['id'] != BREEDS[breed]['id']]).copy())
        self.round = 0
        self.result = None
        self.history = []

    def state(self):
        return dict(player=self.player.data(), enemy=self.enemy.data(), round=self.round,
                    result=self.result, history=self.history[-8:])

    def fallback(self):
        if self.enemy.energy < 20: return 'guard'
        if self.enemy.spirit < 30: return 'provoke'
        return self.rng.choices(list(ACTIONS), weights=[5, 3, 2])[0]

    def step(self, action, enemy_action):
        if self.result: raise ValueError('本场已经结束，请另开一局。')
        if action not in ACTIONS or enemy_action not in ACTIONS: raise ValueError('未知招式')
        if action == 'attack' and self.player.energy < 18: raise ValueError('体力不足，请先固守或挑逗。')
        if enemy_action == 'attack' and self.enemy.energy < 18: enemy_action = 'guard'
        self.round += 1
        events = []
        p, e = self.player, self.enemy
        # Effects and damage are simultaneous, so neither side gets turn-order advantage.
        hits = [0, 0]
        for i, (a, b, move, other) in enumerate([(p,e,action,enemy_action),(e,p,enemy_action,action)]):
            name = '我方' if i == 0 else '对方'
            if move == 'guard':
                a.energy += 24
                a.spirit += 3
            elif move == 'provoke':
                a.energy += 8
                a.spirit += 19
                if other == 'guard':
                    b.spirit -= 15
                    events.append(f'{name}鸣翅示威，压住了对手的气势。')
            else:
                a.energy -= 18
                damage = a.breed['attack'] + self.rng.randint(1, 7) + a.spirit // 15 - b.breed['defense'] // 2
                if other == 'guard': damage = max(3, damage // 3)
                if other == 'provoke': damage += 7
                if self.rng.random() < b.breed['speed'] / 125:
                    damage = 0
                    events.append(f'{name}扑空，对手侧身避开！')
                else:
                    events.append(f'{name}咬合得手，对手耐力 −{damage}。')
                hits[1-i] = damage
                a.spirit -= 5
        for i, f in enumerate([p,e]):
            f.hp = max(0, f.hp-hits[i])
            f.spirit = max(0, min(100,f.spirit - (6 if hits[i] > 0 else 0)))
            f.energy = max(0,min(100,f.energy))
        if p.hp == 0 and e.hp == 0: self.result = 'draw'
        elif e.hp == 0: self.result = 'win'
        elif p.hp == 0: self.result = 'lose'
        elif self.round >= 20:
            left, right = p.hp + p.spirit*.2, e.hp + e.spirit*.2
            self.result = 'draw' if left == right else ('win' if left > right else 'lose')
        entry = dict(round=self.round, player=action, enemy=enemy_action, events=events or ['双方绕盆相持，静待时机。'], damage=hits)
        self.history.append(entry)
        return self.state()
