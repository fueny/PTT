#!/bin/bash

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查是否安装了ffmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    echo "ffmpeg已安装"
else
    echo "ffmpeg未安装，正在安装..."
    sudo apt-get update && sudo apt-get install -y ffmpeg
fi

# 安装依赖包
echo "正在安装依赖包..."
pip3 install -r requirements.txt

echo "环境检查完成"
