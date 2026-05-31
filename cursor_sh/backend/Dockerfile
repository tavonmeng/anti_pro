# 后端镜像
FROM python:3.11-slim

WORKDIR /app
ENV TZ=Asia/Shanghai

# 系统依赖（中文字体用于 PDF 生成）
RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 update \
    && apt-get install -y --no-install-recommends \
    tzdata \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f

# Python 依赖（挂载 pip 缓存，第二次构建秒装）
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 拷贝代码
COPY . .

# 创建必要目录
RUN mkdir -p logs uploads

# 非 root 用户运行（安全最佳实践）
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn app.main:app --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-4} --worker-class uvicorn.workers.UvicornWorker --timeout ${GUNICORN_TIMEOUT:-120} --max-requests 1000 --max-requests-jitter 100"]
