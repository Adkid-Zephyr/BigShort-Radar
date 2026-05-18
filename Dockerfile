# BigShort Radar — Dockerfile
# 用途:让新机一行命令起一套完整环境,无需操心 Python/venv/依赖
# 用法见 README §"快速开始 - Docker 路径"

FROM python:3.9.6-slim-bullseye

# 系统依赖(yfinance 拉数据需要 ca-certificates,sqlite3 命令行调试用)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        sqlite3 \
        tzdata && \
    rm -rf /var/lib/apt/lists/*

# 默认时区(可被 .env 里的 TZ 覆盖)
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# 先复制 requirements 利用 docker layer cache
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 再复制全部源码
COPY . /app

# 数据库 / 日志目录(volume 挂载点)
RUN mkdir -p /app/data /app/logs

# Flask 端口(可被 FLASK_PORT 环境变量覆盖)
EXPOSE 5050

# 默认起 Flask;若需跑 daily_fetch / backfill_history 走 docker-compose run
CMD ["python", "-m", "flask", "--app", "src.web.app", "run", "--host", "0.0.0.0", "--port", "5050"]
