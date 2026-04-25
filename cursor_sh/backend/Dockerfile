# 后端镜像
FROM python:3.9-slim

WORKDIR /app

# 系统依赖（中文字体用于 PDF 生成）
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f

# Python 依赖（利用 Docker 缓存，先装依赖再拷代码）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn

# 拷贝代码
COPY . .

# 创建必要目录
RUN mkdir -p logs uploads

# 非 root 用户运行（安全最佳实践）
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100"]
