FROM python:3.9-slim

WORKDIR /app

# 安装 OCR 和 PDF 渲染所需的系统包
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini .

ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["sh", "-c", "python -m backend.init_db && alembic upgrade head && exec uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
