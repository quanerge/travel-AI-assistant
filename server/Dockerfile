# 旅途管家 FastAPI 后端 - 生产镜像
FROM python:3.11-slim

WORKDIR /app

# 先装依赖，利用层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 暴露端口（与 gunicorn 绑定一致）
EXPOSE 8000

# 使用 gunicorn + uvicorn worker 提供并发能力
# 生产请通过环境变量 CORS_ORIGINS / DATABASE_URL 注入，勿硬编码
CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "-w", "4", \
     "--timeout", "60"]
