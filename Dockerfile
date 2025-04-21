FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装git和必要的构建工具
RUN pip3 install feedparser requests

COPY rss2cubox /app/

# 设置容器启动时执行的命令
CMD ["bash", "runner.sh"]