# 秋鸣 · 斗蟋馆

取意中国传统斗蟋文化的网页策略游戏。宣纸底色、陶制斗盆、程序绘制的蛐蛐与虫鸣，配合 **真实 Laya 多语言模型**驱动的对手决策。

[在线试玩](https://zhihuzheye.site/qiuming/) · [开源仓库](https://github.com/liuqing0224/qiuming-cricket)

## 启动

macOS 上双击 `start.command`，然后打开 http://127.0.0.1:8877 。需要 Python 3.12、Git 和 [uv](https://docs.astral.sh/uv/)。首次运行自动安装依赖，模型首次下载需要网络与约 GB 级磁盘空间。

手动启动：

```sh
uv venv --python 3.12 .venv
mkdir -p vendor
git clone https://github.com/NandhaKishorM/laya.git vendor/laya
git -C vendor/laya checkout c7527708f9f5220c669d8aa385077cd28d04708a
uv pip install --python .venv/bin/python -r requirements-lock.txt -e ./vendor/laya
.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8877
```

前端无需构建。不要直接双击 `index.html`：游戏需要本地 API。本地默认绑定回环地址；生产部署通过 Nginx HTTPS 反向代理与 API 限流，见 [部署文档](deploy/README.md)。

## 玩法

1. 在青背将军（均衡）、紫衣侯（强攻）、金翅郎（灵巧）中选择一只，开盆。
2. 每回合选择强攻 / 固守 / 挑逗，快捷键分别为 1 / 2 / 3。
3. 强攻消耗 18 体力，对挑逗追加伤害；固守恢复 24 体力并抵挡强攻；挑逗提升 19 斗志并压制固守。
4. 耐力为零则退败，双方同时归零为和。20 回合后以 `耐力 + 斗志 × 0.2` 判胜。
5. 结束后可换虫、再战；最近 50 场战绩保存在浏览器 localStorage。

虫鸣默认关闭，由用户点击开启。支持移动端、键盘、减少动态效果偏好。文化氛围为创作性表达，非特定朝代的史实复原；不用真虫，不含真钱下注。

## Laya 接入

用户指定的 [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya) 是 Python 决策模型库。项目调用：

```python
agent = laya.load('convaiinnovations/laya', subfolder='multilingual', device='cpu')
result = agent.predict(pre_turn_state, QUESTIONS)
action = result['answers']['move']['choice']
```

- 服务启动后后台加载模型，页面显示加载或连接状态。
- **只传入出招前状态和已结束回合，绝不传玩家本回合选择。**
- 三选一的 `choice` 输出用于实际对手动作；无体力时由游戏规则限制强攻。
- 模型未加载、推理失败或超过 12 秒时明确切换规则对手，逐回合实录标记来源。超时后不继续堆积推理队列。
- 使用原模型，尚未用斗蟋数据微调；不宣称其具备最优博弈策略或已校准的游戏胜率。
- `LAYA_DISABLE=1` 可仅用规则对手；`LAYA_DEVICE=mps` 可尝试 Apple GPU，默认 CPU 为验收配置。

## 文件与测试

- `game.py`：服务端规则与同时结算。
- `server.py`：FastAPI、会话、Laya 推理与降级。
- `web/`：原生 JavaScript、CSS、Canvas 交互界面。
- `tests/test_game.py`：规则边界、终局、100 场随机模拟与 API 流程。
- `deploy/`：Linux systemd 与 Nginx 配置。

```sh
.venv/bin/python -m pytest -q
```

Laya 源码保存在忽略跟踪的 `vendor/laya` 中，启动脚本会按固定提交恢复。权重保存在 Hugging Face 标准缓存，不复制进项目。第三方许可见 `THIRD_PARTY_NOTICES.md`。

## 开源许可

项目原创代码采用 MIT License。Laya 及模型保留各自原始许可，见 `THIRD_PARTY_NOTICES.md`。
