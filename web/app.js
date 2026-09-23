import {cricket,drawBowl} from './art.js';
const $=s=>document.querySelector(s);
const breeds=[{name:'青背将军',type:'均衡型',color:'#657454',attack:17,defense:8,speed:7,description:'青背金翅，沉稳善战。攻守兼备，适合初入虫场。'},{name:'紫衣侯',type:'强攻型',color:'#766479',attack:22,defense:4,speed:6,description:'紫头阔颚，性烈如火。出手凌厉，须留意体力。'},{name:'金翅郎',type:'灵巧型',color:'#ab8d48',attack:15,defense:6,speed:12,description:'金翅长足，轻捷灵动。善于闪避，伺机反击。'}];
const names={attack:'振翅强攻',guard:'收须固守',provoke:'执草挑逗'};
let selected=0,session=null,state=null,busy=false,animation=null,enemyColor=breeds[1].color;
let records=[];try{const saved=JSON.parse(localStorage.getItem('qiuming-records')||'[]');if(Array.isArray(saved))records=saved.filter(r=>['win','lose','draw'].includes(r.result)&&typeof r.name==='string'&&Number.isFinite(r.round)).slice(0,50)}catch{}
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let audio=null,soundOn=false,chirpTimer=null;
function chirp(){if(!soundOn||!audio)return;const now=audio.currentTime;for(let i=0;i<3;i++){const osc=audio.createOscillator(),gain=audio.createGain();osc.type='sine';osc.frequency.setValueAtTime(3900+i*130,now);gain.gain.setValueAtTime(0,now+i*.10);gain.gain.linearRampToValueAtTime(.025,now+i*.1+.015);gain.gain.exponentialRampToValueAtTime(.0001,now+i*.1+.08);osc.connect(gain);gain.connect(audio.destination);osc.start(now+i*.1);osc.stop(now+i*.1+.09)}}
$('#sound').onclick=async()=>{audio??=new AudioContext();await audio.resume();soundOn=!soundOn;$('#sound').textContent=`虫鸣 · ${soundOn?'开':'关'}`;$('#sound').setAttribute('aria-pressed',String(soundOn));$('#sound').title=soundOn?'关闭虫鸣':'开启虫鸣';clearInterval(chirpTimer);if(soundOn){chirp();chirpTimer=setInterval(chirp,2600)}};
function roster(){
 $('#roster').innerHTML=breeds.map((b,i)=>`<button class="cricket-card ${selected===i?'selected':''}" data-breed="${i}" aria-pressed="${selected===i}" ${session&&!state?.result?'disabled':''}><canvas width="150" height="150" aria-hidden="true"></canvas><span><b>${b.name}</b><small>${b.type}</small><span class="card-stats">攻 ${b.attack} · 守 ${b.defense} · 敏 ${b.speed}</span></span>${selected===i?'<span class="selection-dot">✓</span>':''}</button>`).join('');
 document.querySelectorAll('[data-breed]').forEach((button,i)=>{cricket(button.querySelector('canvas').getContext('2d'),64,76,.65,breeds[i].color,1,0);button.onclick=()=>{selected=i;roster();$('#player-name').textContent=breeds[i].name;$('#player-type').textContent=breeds[i].type;$('#breed-description').textContent=breeds[i].description;}});
 $('#breed-description').textContent=breeds[selected].description;
}
async function api(path,body){const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),18000);try{const r=await fetch(path.replace(/^\//,''),{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,signal:controller.signal});const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'请求未能完成，请重试。');return data}finally{clearTimeout(timer)}}
function buttons(){document.querySelectorAll('[data-action]').forEach(b=>b.disabled=!session||!!state?.result||busy||(b.dataset.action==='attack'&&state.player.energy<18));$('#start').disabled=busy||!!session&&!state?.result;$('#start').innerHTML=state?.result?'再斗一场 <span>→</span>':busy?'正在开盆…':'开盆斗虫 <span>→</span>';}
function render(){
 for(const side of ['player','enemy']){const f=state[side];$(`#${side}-name`).textContent=f.breed.name;$(`#${side}-type`).textContent=f.breed.title;$(`#${side}-hp`).style.width=f.hp+'%';$(`#${side}-hp-label`).textContent=`耐力 ${f.hp} / 100`}
 $('#round-label').textContent=`第 ${String(state.round).padStart(2,'0')} 回合 / 20`;
 for(const [key,id] of [['energy','energy'],['spirit','spirit']]){$('#'+id).textContent=state.player[key];$('#'+id+'-bar').style.width=state.player[key]+'%'}
 $('#stage-label').textContent=state.result?'终场 · 胜负已定':busy?'交锋 · 观其进退':'斗虫 · 请君出招';
 $('#control-title').textContent=state.result?'胜负已分，且待再会。':busy?'两虫相试，稍候片刻…':'观其势，择一招。';
 enemyColor=state.enemy.breed.color;
 buttons();
}
function showError(error){$('#scene-message').textContent=error.name==='AbortError'?'等候超时，请刷新后重新开局。':`未能完成：${error.message}`;}
$('#start').onclick=async()=>{busy=true;buttons();try{const data=await api('/api/start',{breed:selected});session=data.session;state=data;$('#result').hidden=true;$('#log').innerHTML='<div class="log-entry"><small>良虫入盆</small><h3>两雄相会，各显其能</h3><p>试探一招，看看对手的虚实。</p></div>';$('#scene-message').textContent='良虫入盆，请选择你的第一招。';roster();}catch(e){showError(e)}finally{busy=false;if(state)render();else buttons()}};
async function act(action){if(busy||!session||state.result||(action==='attack'&&state.player.energy<18))return;busy=true;render();$('#scene-message').textContent='执草相邀，两虫试探中…';try{
 const next=await api('/api/turn',{session,action});const entry=next.history.at(-1);animation={start:performance.now(),player:entry.player,enemy:entry.enemy};chirp();
 await new Promise(r=>setTimeout(r,reduced?0:850));state=next;
 const item=document.createElement('div');item.className='log-entry';const title=document.createElement('h3');title.textContent=`${names[entry.player]} · ${names[entry.enemy]}`;const small=document.createElement('small');small.textContent=`第 ${entry.round} 回合 · ${next.decision_source==='laya'?'Laya 决策':'规则对手'}`;const p=document.createElement('p');p.textContent=entry.events.join(' ');item.append(small,title,p);$('#log').prepend(item);while($('#log').children.length>8)$('#log').lastChild.remove();$('#log').scrollTop=0;
 $('#scene-message').textContent=entry.events[0];
 if(next.result)finish();
 }catch(e){showError(e)}finally{busy=false;render()}}
function finish(){const result=state.result;$('#result').hidden=false;$('#result-title').textContent={win:'此战告捷',lose:'惜败一场',draw:'棋逢对手'}[result];$('#result-sub').textContent=`第 ${state.round} 回合 · 收盆`;$('#result-copy').textContent={win:`${state.player.breed.name}鸣翅而立，赢得满堂喝彩。`,lose:'胜负乃常事。养精蓄锐，再赴秋日之约。',draw:'双方难分高下，此局以和为贵。'}[result];records.unshift({name:state.player.breed.name,result,round:state.round,date:new Date().toLocaleDateString('zh-CN')});records=records.slice(0,50);try{localStorage.setItem('qiuming-records',JSON.stringify(records))}catch{}updateRecordSummary();roster()}
function updateRecordSummary(){const wins=records.filter(r=>r.result==='win').length;$('#record-summary').textContent=records.length?`已斗 ${records.length} 场 · 胜 ${wins} 场`:'尚无战绩 · 静候首胜'}
for(const button of document.querySelectorAll('[data-action]'))button.onclick=()=>act(button.dataset.action);
document.addEventListener('keydown',e=>{if($('#modal').open||e.repeat||e.ctrlKey||e.metaKey||e.altKey)return;const action={'1':'attack','2':'guard','3':'provoke'}[e.key];if(action){e.preventDefault();act(action)}});
const guide=`<h2>执草入门</h2><p>选好一只蛐蛐，点击「开盆斗虫」。每回合选择一招，双方同时结算，先耗尽对方耐力者胜。</p><h3>三招相生，知进知退</h3><ul><li><b>振翅强攻</b>：消耗 18 体力，打击对方耐力；对挑逗中的对手追加 7 点伤害。</li><li><b>收须固守</b>：恢复 24 体力、3 斗志，受到的强攻伤害约为三分之一。</li><li><b>执草挑逗</b>：恢复 8 体力、19 斗志；对手固守时，额外压低其 15 斗志。</li></ul><p>斗志越高，进攻越有力；灵敏越高，越可能闪避。耐力归零即退败；第二十回合按「剩余耐力 + 斗志 × 0.2」判胜，同分为和。快捷键 1 / 2 / 3 可出招。</p><p>这是取意传统斗蟋的虚拟策略游戏，属性与规则均为游戏设计。对手使用 Laya 选择动作；模型加载中或不可用时，实录会标明「规则对手」。战绩仅保存在本机浏览器。</p>`;
function modal(html){$('#modal-body').innerHTML=html;$('#modal').showModal()}
$('#guide').onclick=()=>modal(guide);$('#arena-nav').onclick=()=>$('.arena').scrollIntoView({behavior:reduced?'instant':'smooth',block:'center'});
$('#collection-nav').onclick=()=>modal('<h2>秋虫三品</h2><p>虫有其性，善用方能取胜。以下为游戏内品类设定。</p>'+breeds.map(b=>`<h3>${b.name} · ${b.type}</h3><p>${b.description}<br>攻击 ${b.attack}　防御 ${b.defense}　灵敏 ${b.speed}</p>`).join(''));
$('#records-nav').onclick=()=>{modal('<h2>斗虫战绩簿</h2><p>记一场秋趣，留一段虫鸣。</p><div id="records-list"></div>');const list=$('#records-list');if(!records.length){list.textContent='尚未开张。去斗虫台，写下你的第一场吧。';return}for(const r of records){const row=document.createElement('div');row.className='record-row';const name=document.createElement('span');name.textContent=r.name;const info=document.createElement('small');info.textContent=`${r.round} 回合 · ${r.date||''}`;const result=document.createElement('b');result.textContent={win:'胜',lose:'负',draw:'和'}[r.result];row.append(name,info,result);list.append(row)}};
$('#close-modal').onclick=()=>$('#modal').close();$('#modal').onclick=e=>{if(e.target===$('#modal')){const r=$('#modal').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('#modal').close()}};
async function modelStatus(){try{const model=await api('/api/status');$('#engine-status').textContent=model.status==='ready'?'Laya · 多语言模型已连接':model.status==='loading'?'Laya 加载中 · 规则对手可用':'规则对手 · Laya 暂未连接';$('#engine-dot').style.background=model.status==='ready'?'#6d895e':'#b49461';$('#engine-mobile').textContent=$('#engine-status').textContent;if(model.status==='loading')setTimeout(modelStatus,5000)}catch{$('#engine-status').textContent='服务未连接 · 请启动本地服务';$('#engine-mobile').textContent=$('#engine-status').textContent;setTimeout(modelStatus,10000)}}
const canvas=$('#arena-canvas'),ctx=canvas.getContext('2d');let width=0,height=0;
new ResizeObserver(()=>{const rect=canvas.getBoundingClientRect();width=rect.width;height=rect.height;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=width*dpr;canvas.height=height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0)}).observe(canvas);
function frame(time){if(width&&height&&!document.hidden)drawBowl(ctx,width,height,time/1000,{player:breeds[selected].color,enemy:enemyColor,animation,result:state?.result,reduced});requestAnimationFrame(frame)}
roster();updateRecordSummary();modelStatus();requestAnimationFrame(frame);
