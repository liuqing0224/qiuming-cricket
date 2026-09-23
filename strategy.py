"""Bounded, auditable hybrid policy; model predictions never see a pending human move."""
from collections import Counter
import math

from game import ACTIONS, resolve_exchange

PERSONAS = {
    'bold': dict(name='急先锋', style='抢攻压迫', description='宁可换伤，也要抢先压低你的耐力。', offense=1.3, defense=.8, energy=.10, spirit=.10, exploration=.08),
    'patient': dict(name='守拙翁', style='蓄力反击', description='重视体力与退路，等你疲惫再出手。', offense=.9, defense=1.45, energy=.27, spirit=.14, exploration=.03),
    'reader': dict(name='听风客', style='察势拆招', description='盯住你最近的习惯，善于蓄势后变招。', offense=1.0, defense=1.05, energy=.17, spirit=.25, exploration=.12),
}
PLANS = {'press': '乘势施压', 'conserve': '留力周旋', 'unsettle': '蓄势扰敌'}
QUESTIONS = {
    'forecast': {
        'type': 'choice',
        'instructions': '根据玩家过去的出招、体力和局势，预测玩家下一招。没有本回合出招信息；只作预测。',
        'criteria': {'attack': '玩家可能强攻', 'guard': '玩家可能固守回体力', 'provoke': '玩家可能挑逗涨斗志'},
    },
    'plan': {
        'type': 'choice',
        'instructions': '根据馆主性格与当前局势，选择馆主本回合战术目标。',
        'criteria': {'press': '乘势施压，争取伤害或收尾', 'conserve': '留力周旋，防伤并恢复体力', 'unsettle': '蓄势扰敌，提高斗志打破僵持'},
    },
}


def public_persona(key):
    return dict(id=key, **{k: PERSONAS[key][k] for k in ('name', 'style', 'description')})


def normalise(values, labels):
    if not isinstance(values, dict) or set(values) != set(labels):
        raise ValueError('Incomplete decision distribution')
    numbers = {k: float(values[k]) for k in labels}
    if any(not math.isfinite(v) or v < 0 for v in numbers.values()) or sum(numbers.values()) <= 0:
        raise ValueError('Invalid decision probabilities')
    total = sum(numbers.values())
    return {k: v / total for k, v in numbers.items()}


def model_signals(result):
    answers = result['answers']
    forecast = normalise(answers['forecast']['probabilities'], ACTIONS)
    plan = answers['plan']['choice']
    if plan not in PLANS:
        raise ValueError('Invalid tactical plan')
    return dict(forecast=forecast, plan=plan)


def observations(match):
    recent = [r['player'] for r in match.history[-6:]]
    counts = Counter(recent)
    streak = 0
    for move in reversed(recent):
        if move != recent[-1]: break
        streak += 1
    if not recent:
        note = '尚无已出招记录，先按双方状态试探。'
    else:
        parts = [f'{ACTIONS[a]} {counts[a]} 次' for a in ACTIONS if counts[a]]
        note = f'此前 {len(recent)} 回合：' + '，'.join(parts) + '。'
        if streak >= 2:
            note += f'末尾连续 {streak} 次{ACTIONS[recent[-1]]}。'
    return dict(rounds=len(recent), sequence=recent, counts={a: counts[a] for a in ACTIONS}, streak=streak, note=note)


def decision_context(match):
    """Explicit allowlist, detached scalars: no session, history metadata or submitted action."""
    def fighter(f):
        return {'耐力': f.hp, '体力': f.energy, '斗志': f.spirit,
                '攻击': f.breed['attack'], '防御': f.breed['defense'], '灵敏': f.breed['speed']}
    seen = observations(match)
    return {
        '馆主': PERSONAS[match.persona]['name'], '性格': PERSONAS[match.persona]['description'],
        '馆主虫': fighter(match.enemy), '玩家虫': fighter(match.player),
        '已结束回合': match.round, '玩家最近出招': [ACTIONS[a] for a in seen['sequence']],
        '规则': '强攻耗18体力，固守回24体力并减伤，挑逗回8体力涨19斗志。强攻破挑逗，固守卸强攻，挑逗压固守。20回合按耐力加斗志的五分之一判胜。',
    }


def empirical_forecast(match):
    # A recency-weighted, smoothed within-match memory, not a learned player identity.
    counts = dict(attack=1.5, guard=1.0, provoke=1.0)
    for i, row in enumerate(match.history[-6:]):
        counts[row['player']] += 1 + i*.35
    if match.player.energy < 18:
        counts['attack'] = 0
        counts['guard'] += 3
    elif match.player.energy < 35:
        counts['guard'] += 2
    if match.player.spirit < 25: counts['provoke'] += 1.5
    return normalise(counts, ACTIONS)


def outcome_value(match, human, enemy, p_next, e_next, persona, plan):
    p, e = match.player, match.enemy
    damage = p.hp - p_next.hp
    suffered = e.hp - e_next.hp
    offense = persona['offense'] + (.22 if plan == 'press' else 0)
    defense = persona['defense'] + (.22 if plan == 'conserve' else 0)
    energy_weight = persona['energy'] + (.35 if e.energy < 36 else 0)
    spirit_weight = persona['spirit'] + (.10 if plan == 'unsettle' else 0)
    score = damage*offense - suffered*defense
    score += (e_next.energy-e.energy)*energy_weight
    score += (e_next.spirit-e.spirit)*spirit_weight + (p.spirit-p_next.spirit)*.12
    if match.round >= 17:
        score += ((e_next.hp-p_next.hp) + .2*(e_next.spirit-p_next.spirit))*.6
    if p_next.hp <= 0 and e_next.hp > 0: score += 100
    elif e_next.hp <= 0 and p_next.hp > 0: score -= 130
    # Future attack readiness gives guard/provoke a real horizon beyond this turn.
    score += .8 * (min(3, e_next.energy//18)-min(3, e.energy//18))
    return score


def score_actions(match, forecast, persona, plan):
    legal = [a for a in ACTIONS if a != 'attack' or match.enemy.energy >= 18]
    scores, expected = {}, {}
    for action in legal:
        score = outgoing = incoming = 0
        for human, weight in forecast.items():
            if weight == 0: continue
            p_next, e_next, _ = resolve_exchange(match.player, match.enemy, human, action)
            score += weight*outcome_value(match, human, action, p_next, e_next, persona, plan)
            outgoing += weight*(match.player.hp-p_next.hp)
            incoming += weight*(match.enemy.hp-e_next.hp)
        scores[action] = score
        expected[action] = dict(outgoing=round(outgoing,1), incoming=round(incoming,1))
    return scores, expected


def choose_decision(match, signals=None, fallback_reason=None):
    seen = observations(match)
    persona = PERSONAS[match.persona]
    forecast = empirical_forecast(match)
    plan = ('conserve' if match.enemy.energy < 36 else 'unsettle' if match.enemy.spirit < 35 else 'press')
    rules_scores, _ = score_actions(match, forecast, persona, plan)
    rules_choice = max(rules_scores, key=rules_scores.get)
    if signals:
        # Model scores are uncalibrated: cap influence, never present them as win odds.
        forecast = {a: .65*forecast[a]+.35*signals['forecast'][a] for a in ACTIONS}
        plan = signals['plan']
    if match.player.energy < 18:
        forecast['attack'] = 0
        if sum(forecast.values()) == 0: forecast.update(guard=1, provoke=1)
        forecast = normalise(forecast, ACTIONS)
    scores, expected = score_actions(match, forecast, persona, plan)
    legal = list(scores)
    best = max(scores, key=scores.get)
    # Small, declared personality variation only among near-equivalent actions.
    near = [a for a in legal if scores[a] >= scores[best]-2]
    action = match.rng.choice(near) if match.rng.random() < persona['exploration'] else best
    predicted = max(forecast, key=forecast.get)
    reasons = {
        'attack': '本招重在压低对方耐力，挑逗中的对手会承受额外伤害。',
        'guard': '本招重在降低受伤并恢复体力，为后续强攻留力。',
        'provoke': '本招重在提高斗志；遇到固守还可压低对方斗志。',
    }
    return dict(
        action=action, source='laya' if signals else 'rules',
        mode='Laya 判断 + 局面推演' if signals else '记忆规则 + 局面推演',
        fallback_reason=fallback_reason if not signals else None,
        persona=public_persona(match.persona), based_on_round=match.round,
        observation=seen, forecast={k: round(v,4) for k,v in forecast.items()},
        predicted=predicted, plan=plan, plan_label=PLANS[plan],
        model_forecast=signals['forecast'] if signals else None,
        model_plan=signals['plan'] if signals else None,
        scores={k:round(v,2) for k,v in scores.items()}, expected=expected,
        explanation=reasons[action], varied=action != best,
        rules_choice=rules_choice, model_changed_ranking=bool(signals and best != rules_choice),
    )
