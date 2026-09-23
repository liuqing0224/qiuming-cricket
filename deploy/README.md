# Linux 部署

生产使用 Python 3.12、CPU 版 PyTorch、单个 Uvicorn worker、systemd 和 Nginx。推荐至少 4 GB 内存；模型首次加载/下载需要网络。

## 安装

将项目放入 `/opt/qiuming/app`，根据项目 README 拉取固定版本的 `vendor/laya`，安装 [uv](https://docs.astral.sh/uv/)。Python 本体必须位于服务账号可读的路径，例如 `/opt/qiuming/python`，不要放在 `/root` 下。

```sh
uv python install --install-dir /opt/qiuming/python 3.12
# 将下一行 Python 路径替换为上一步安装结果中的 bin/python3.12
uv venv --python /opt/qiuming/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12 /opt/qiuming/venv
uv pip install --python /opt/qiuming/venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu
cd /opt/qiuming/app
uv pip install --python /opt/qiuming/venv/bin/python -r requirements.txt
useradd --system --home /var/lib/qiuming --create-home --shell /usr/sbin/nologin qiuming
mkdir -p /var/lib/qiuming/huggingface
chown -R qiuming:qiuming /var/lib/qiuming
cp deploy/qiuming.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now qiuming
```

模型由服务以 `qiuming` 账号下载到 `/var/lib/qiuming/huggingface`。`GET /api/status` 为 `ready` 时才表示真实 Laya 就绪；`loading`、`fallback` 不表示推理成功。可用 `LAYA_MODEL_PATH` 指定本地模型根目录（其中包含 `multilingual/`）。

## HTTPS 反向代理

1. 将 `qiuming-rate.conf` 放到 `/etc/nginx/conf.d/`。
2. 将 `qiuming.nginx.conf` 放到 `/etc/nginx/snippets/qiuming.conf`。
3. 在已配置证书的目标 `server` 块里加入 `include /etc/nginx/snippets/qiuming.conf;`。
4. 备份原配置，执行 `nginx -t && systemctl reload nginx`。

游戏地址是 `https://你的域名/qiuming/`。静态资源、API 使用相对 URL，也支持根路径运行。API 限流每 IP 每秒 2 次、突发 12 次；请求体最大 8 KB。后端仅监听回环，不必开放额外公网端口。

## 验证和运维

```sh
systemctl status qiuming
journalctl -u qiuming -n 50 --no-pager
curl http://127.0.0.1:8877/api/status
curl https://你的域名/qiuming/api/status
```

验证页面、开盆、真实 `decision_source: laya` 回合和最终胜负。只有单 worker 可保持当前内存会话一致；重启会丢失进行中的对局，浏览器战绩不受影响。模型忙碌时明确降级到规则对手。

服务有 2300 MB 内存上限和 180% CPU 上限。可按主机资源调整；不要在已有生产服务的小机器上盲目增加 worker。更新代码后 `systemctl restart qiuming`，再检查 ready 与真实回合。回滚时恢复应用备份、重启，并恢复 Nginx 备份后先做 `nginx -t`。

## 许可

原创代码 MIT；Laya 源码 Apache-2.0，完整声明见 `THIRD_PARTY_NOTICES.md`。不要提交 SSH 私钥、环境凭据、虚拟环境或模型权重。

### 小内存主机的加载峰值

在 4 GB、无 swap 主机上，Laya 的 float32 初始化可能因同时持有模型与权重超过服务内存上限。已验证的部署使用额外 2 GB swap 缓冲加载峰值，保留 `MemoryMax=2300M`。只有在磁盘空间足够、主机允许时执行，已有 swap 可复用；不要覆盖已有文件：

```sh
fallocate -l 2G /var/lib/qiuming.swap
chmod 600 /var/lib/qiuming.swap
mkswap /var/lib/qiuming.swap
swapon /var/lib/qiuming.swap
# 需要重启后生效时，将下行追加一次到 /etc/fstab：
# /var/lib/qiuming.swap none swap sw 0 0
```

加载后检查 `systemctl show qiuming -p NRestarts -p MemoryCurrent`，必须确认不再 OOM 重启；也必须验证真实 `decision_source: laya`，不能只看页面可访问。
