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
from typing import Literal
from game import Match, ACTIONS
from strategy import PERSONAS, QUESTIONS, public_persona, decision_context, model_signals, choose_decision

ROOT = Path(__file__).parent
log = logging.getLogger('uvicorn.error')
MODEL = {'status': 'loading', 'name': 'Laya multilingual', 'detail': '正在加载本地决策模型'}
agent = None
pool = ThreadPoolExecutor(max_workers=1)
inference = None
sessions = {}

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
        agent.cfg['max_len'] = 512
        agent.cfg['head_max_len'] = 192
        MODEL.update(status='ready', detail='Laya 多语言模型已就绪')
        log.info('Laya ready')
    except Exception as exc:
        MODEL.update(status='fallback', detail='模型暂不可用，使用规则对手')
        log.warning('Laya loading failed: %s', type(exc).__name__)

@asynccontextmanager
async def lifespan(app):
    global pool, inference
    pool = ThreadPoolExecutor(max_workers=1)
    inference = None
    loop = asyncio.get_running_loop()
    loop.run_in_executor(pool, load_model)
    yield
    pool.shutdown(wait=False, cancel_futures=True)

app = FastAPI(lifespan=lifespan)

class Start(BaseModel):
    breed: int = Field(ge=0, le=2)
    persona: Literal['bold', 'patient', 'reader'] = 'reader'
class Turn(BaseModel):
    session: str = Field(min_length=16, max_length=64)
    action: str

@app.get('/api/status')
def status(): return MODEL

@app.get('/api/personas')
def personas(): return [public_persona(key) for key in PERSONAS]

@app.post('/api/start')
async def start(body: Start):
    now = time.monotonic()
    for sid in list(sessions):
        if now - sessions[sid]['touched'] > 7200: del sessions[sid]
    if len(sessions) >= 1000: raise HTTPException(503, '虫馆已满，请稍后再试。')
    sid = secrets.token_urlsafe(24)
    match = Match(body.breed, persona=body.persona)
    sessions[sid] = dict(match=match, lock=asyncio.Lock(), touched=now)
    return dict(session=sid, **match.state())

def predict(state):
    # Two typed judgments in one batch, using only detached pre-turn context.
    return model_signals(agent.predict(state, QUESTIONS))

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
        signals = None
        fallback_reason = '模型加载中' if MODEL['status'] == 'loading' else '模型暂不可用'
        if MODEL['status'] == 'ready':
            fallback_reason = '模型忙碌，本回合改用记忆规则'
            if inference is None or inference.done():
                context = decision_context(match)
                inference = asyncio.get_running_loop().run_in_executor(pool, predict, context)
                try:
                    signals = await asyncio.wait_for(asyncio.shield(inference), timeout=12)
                except asyncio.TimeoutError:
                    fallback_reason = '模型超时，本回合改用记忆规则'
                except Exception as exc:
                    fallback_reason = '模型输出不可用，本回合改用记忆规则'
                    log.warning('Decision failed: %s', type(exc).__name__)
        decision = choose_decision(match, signals, fallback_reason)
        match.step(body.action, decision['action'])
        # Reveal the sealed pre-turn judgment only after both moves have resolved.
        decision.update(round=match.round, actual=body.action,
                        forecast_hit=decision['predicted'] == body.action)
        match.decisions.append(decision)
        entry['touched'] = time.monotonic()
        return dict(**match.state(), decision_source=decision['source'])

app.mount('/', StaticFiles(directory=ROOT/'web', html=True), name='web')
