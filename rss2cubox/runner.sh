#!/bin/bash

# 记录脚本启动
echo "RSS to Cubox 自动运行脚本启动于 $(date)"

# 切换到脚本所在目录，确保相对路径正确
cd "$(dirname "$0")"

# 无限循环，每30分钟运行一次
while true; do
    echo "------------------------------------"
    echo "开始运行 RSS 转发任务 - $(date)"
    
    # 运行 Python 脚本
    # 如果使用虚拟环境，可以取消下面的注释并修改路径
    # source /path/to/venv/bin/activate
    
    python3 main.py
    
    echo "RSS 转发任务结束 - $(date)"
    echo "等待 30 分钟后再次运行..."
    echo "------------------------------------"
    
    # 等待 30 分钟 (1800 秒)
    sleep 1800
done