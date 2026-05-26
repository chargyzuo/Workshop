#!/bin/bash

echo "============================================="
echo "  macOS NAT 测试工具 (基于 pystun3)"
echo "============================================="
echo "[1/3] 正在创建临时隔离环境以避免污染全局 Python..."

VENV_DIR=".temp_stun_venv"
# 确保清理旧的遗留文件夹
rm -rf $VENV_DIR
python3 -m venv $VENV_DIR

# 激活虚拟环境
source $VENV_DIR/bin/activate

echo "[2/3] 正在安装 pystun3 (需要几秒钟)..."
# 使用清华源加速安装
pip install pystun3 -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet

echo "[3/3] 正在测试 NAT 类型，请稍候..."
echo "---------------------------------------------"

# 使用国内比较稳定的腾讯 STUN 服务器
pystun3

echo "---------------------------------------------"
echo "测试完毕！正在清理临时文件..."
deactivate
rm -rf $VENV_DIR

echo "清理完成。"
