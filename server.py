import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import secrets
import time

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from game import Match, ACTIONS

ROOT = Path(__file__).parent
log = logging.getLogger('uvicorn.error')
MODEL = {'status': 'loading', 'name': 'Laya multilingual', 'detail': '正在加载本地决策模型'}
agent = None
pool = ThreadPoolExecutor(max_workers=1)
inference = None
sessions = {}
QUESTIONS = {'move': {'type': 'choice', 'instructions': '选择斗蛐蛐比赛中下一回合最合适的招式。体力不足时固守，斗志低时挑逗，状态良好时进攻。', 'criteria': {'attack': '振翅进攻：消耗18体力造成伤害，克制挑逗。', 'guard': '固守：恢复24体力，大幅减少进攻伤害。', 'provoke': '挑逗：恢复8体力和19斗志，压制固守，但怕进攻。'}}}

def load_model():
    global agent
    if os.environ.get('LAYA_DISABLE') == '1':
        MODEL.update(status='fallback', detail='已选择规则对手模式')
        return
    try:
        import torch
        import laya
        torch.set_num_threads(int(os.environ.get("LAYA_THREADS", "2")))
        agent = laya.load(os.environ.get('LAYA_MODEL_PATH', 'convaiinnovations/laya'), subfolder='multilingual', device=os.environ.get('LAYA_DEVICE','cpu'))
        MODEL.update(status='ready', detail='Laya 多语言模型已就绪')
        log.info('Laya ready')
    except Exception as exc:
        MODEL.update(status='fallback', detail='模型暂不可用，使用规则对手')
        log.warning('Laya loading failed: %s', type(exc).__name__)

@asynccontextmanager
async def lifespan(app):
    loop = asyncio.get_running_loop()
    loop.run_in_executor(pool, load_model)
    yield
    pool.shutdown(wait=False, cancel_futures=True)

app = FastAPI(lifespan=lifespan)

class Start(BaseModel):
    breed: int = Field(ge=0, le=2)
class Turn(BaseModel):
    session: str = Field(min_length=16, max_length=64)
    action: str

@app.get('/api/status')
def status(): return MODEL

@app.post('/api/start')
async def start(body: Start):
    now = time.monotonic()
    for sid in list(sessions):
        if now - sessions[sid]['touched'] > 7200: del sessions[sid]
    if len(sessions) >= 1000: raise HTTPException(503, '虫馆已满，请稍后再试。')
    sid = secrets.token_urlsafe(24)
    match = Match(body.breed)
    sessions[sid] = dict(match=match, lock=asyncio.Lock(), touched=now)
    return dict(session=sid, **match.state())

def predict(state):
    # Only the pre-turn state reaches the model. The player's pending move is never sent.
    result = agent.predict(state, QUESTIONS)
    answer = result['answers']['move']
    choice = answer['choice']
    if choice not in ACTIONS: raise ValueError('Invalid model choice')
    return choice

@app.post('/api/turn')
async def turn(body: Turn):
    global inference
    entry = sessions.get(body.session)
    if not entry: raise HTTPException(404, '对局已过期，请重新开局。')
    if entry['lock'].locked(): raise HTTPException(409, '上一回合尚未结束。')
    async with entry['lock']:
        match = entry['match']
        if body.action not in ACTIONS: raise HTTPException(422, '未知招式')
        if match.result: raise HTTPException(409, '本场已经结束，请另开一局。')
        if body.action == 'attack' and match.player.energy < 18: raise HTTPException(422, '体力不足，请先固守或挑逗。')
        choice = match.fallback()
        source = 'rules'
        if MODEL['status'] == 'ready' and (inference is None or inference.done()):
            state = {'我方': match.enemy.data(), '对手': match.player.data(), '回合': match.round+1, '上回合': match.history[-1:]}
            inference = asyncio.get_running_loop().run_in_executor(pool, predict, state)
            try:
                choice = await asyncio.wait_for(asyncio.shield(inference), timeout=12)
                source = 'laya'
            except Exception:
                # Shield avoids cancelling a still-running inference. Do not queue more work.
                source = 'rules'
        state = match.step(body.action, choice)
        entry['touched'] = time.monotonic()
        return dict(**state, decision_source=source)

app.mount('/', StaticFiles(directory=ROOT/'web', html=True), name='web')
