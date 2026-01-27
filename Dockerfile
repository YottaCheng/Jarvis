# 使用官方轻量级 Python 环境
FROM python:3.11-slim

# 设置容器内的工作目录
WORKDIR /app

# 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有代码
COPY . .

# 启动命令
CMD ["python", "main.py"]