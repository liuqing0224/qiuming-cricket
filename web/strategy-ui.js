const $ = selector => document.querySelector(selector);
const names = {attack:'强攻', guard:'固守', provoke:'挑逗'};
const plans = {press:'乘势施压', conserve:'留力周旋', unsettle:'蓄势扰敌'};
const add = (parent, tag, text, className='') => {
  const node = document.createElement(tag);
  node.textContent = text;
  node.className = className;
  parent.append(node);
  return node;
};

export async function loadPersonas(api, onSelect) {
  const select = $('#persona');
  // Bind immediately, even when the catalog API is slow or unavailable.
  let personas = [...select.options].map(option => ({
    id: option.value,
    name: option.textContent.split(' · ')[0],
    style: option.textContent.split(' · ')[1],
    description: option.dataset.description || '',
  }));
  const describe = () => {
    const persona = personas.find(p => p.id === select.value);
    if (!persona) return;
    $('#persona-description').textContent = persona.description;
    onSelect(persona);
  };
  select.addEventListener('change', describe);
  describe();
  try {
    const catalog = await api('/api/personas');
    if (!Array.isArray(catalog) || !catalog.length) return;
    // Do not reset a choice made while this request was in flight.
    const selected = select.value;
    personas = catalog;
    select.replaceChildren();
    for (const p of personas) select.add(new Option(`${p.name} · ${p.style}`, p.id));
    select.value = personas.some(p => p.id === selected) ? selected : personas[0].id;
    describe();
  } catch {
    // The built-in catalog still provides immediate preview and selection.
  }
}

export function resetDecision() {
  $('#decision-round').textContent = '每回合结束后揭晓';
  $('#decision-source').textContent = '尚未交锋';
  $('#decision-observation').textContent = '只记住本局已经出过的招，不读取你正在选择的动作。';
  $('#decision-plan').textContent = '察其往招，再择应对。';
  $('#decision-reason').textContent = '对手会结合性格、体力和斗志评估攻守。';
  $('#forecast').replaceChildren();
  $('#forecast-result').textContent = '开盆后，查看对手对已结束回合的判断。';
  $('#review').disabled = true;
}

export function renderDecision(state) {
  $('#persona').disabled = !state.result;
  $('#enemy-resources').textContent = `体力 ${state.enemy.energy} · 斗志 ${state.enemy.spirit}`;
  $('#rival-title').textContent = state.persona.name;
  const d = state.decision;
  if (!d) return;
  $('#review').disabled = false;
  $('#decision-round').textContent = `第 ${d.round} 回合复盘 · 依据前 ${d.based_on_round} 回合`;
  $('#decision-source').textContent = d.mode;
  $('#decision-observation').textContent = d.observation.note;
  $('#decision-plan').textContent = `${d.persona.name} · ${d.plan_label} → ${names[d.action]}`;
  $('#decision-reason').textContent = d.fallback_reason ? `${d.fallback_reason}。${d.explanation}` : d.explanation;
  const forecast = $('#forecast');
  forecast.replaceChildren();
  for (const action of Object.keys(names)) {
    const row = add(forecast, 'div', '', 'forecast-row');
    add(row, 'span', names[action]);
    const meter = document.createElement('meter');
    meter.min = 0; meter.max = 1; meter.value = d.forecast[action];
    meter.setAttribute('aria-label', `${names[action]}预测倾向`);
    row.append(meter);
    add(row, 'small', `${Math.round(d.forecast[action]*100)}%`);
  }
  $('#forecast-result').textContent = `预判你会${names[d.predicted]}，实际${names[d.actual]} · ${d.forecast_hit?'猜中':'未猜中'}`;
}

export function renderReview(container, decisions) {
  add(container, 'h2', '看招 · 战术复盘');
  if (!decisions.length) {
    add(container, 'p', '完成一个回合，就能查看双方的判断与应对。');
    return;
  }
  const modelRounds = decisions.filter(d=>d.source==='laya').length;
  const hits = decisions.filter(d=>d.forecast_hit).length;
  add(container, 'p', `已记录 ${decisions.length} 回合，Laya 参与 ${modelRounds} 回合，出招预测猜中 ${hits} 次。记录只属于本局。`);
  add(container, 'p', '预测倾向由历史统计与 Laya 判断融合，未做概率校准，不是胜率。以下战术说明来自规则计算，不是模型原话。', 'review-note');
  for (const d of [...decisions].reverse()) {
    const row = add(container, 'section', '', 'review-entry');
    add(row, 'small', `第 ${d.round} 回合 · ${d.mode} · 只看到前 ${d.based_on_round} 回合`);
    add(row, 'h3', `${d.persona.name}使${names[d.action]}，你使${names[d.actual]}`);
    add(row, 'p', d.observation.note);
    if (d.model_forecast) {
      const predicted = Object.keys(d.model_forecast).reduce((best,a)=>d.model_forecast[a]>d.model_forecast[best]?a:best,'attack');
      add(row, 'p', `Laya 原始选择：预测${names[predicted]}，战术「${plans[d.model_plan]}」。融合历史后预判${names[d.predicted]}，${d.forecast_hit?'猜中':'未猜中'}。`);
    } else {
      add(row, 'p', `规则预判${names[d.predicted]}，${d.forecast_hit?'猜中':'未猜中'}。${d.fallback_reason || '本回合未使用模型'}。`);
    }
    add(row, 'p', d.explanation);
    if (d.source === 'laya') add(row, 'p', `无模型时首选${names[d.rules_choice]}；${d.model_changed_ranking?'模型判断改变了招式收益排序。':'模型判断未改变首选招式。'}`);
    const details = add(row, 'details', '');
    add(details, 'summary', '展开招式比较');
    add(details, 'p', '收益值是依据伤害、体力、斗志与馆主偏好计算的相对分数，越高越优；不是胜率。');
    for (const [move,value] of Object.entries(d.scores)) {
      const effect = d.expected[move];
      add(details, 'div', `${names[move]}：${value.toFixed(1)} 分 · 预计造成 ${effect.outgoing} / 承受 ${effect.incoming} 伤害`, 'score-row');
    }
    if (d.varied) add(details, 'p', '本回合在收益接近的招式中进行了性格变招。');
  }
}
