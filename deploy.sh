#!/bin/bash
# DevOps 一键部署脚本

echo "==================== 开始自动化部署 ===================="

# 1. 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "安装 Docker..."
    yum install -y docker || apt install -y docker-ce docker-ce-cli containerd.io
    systemctl start docker
    systemctl enable docker
fi

# 2. 检查Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "安装 Docker Compose..."
    curl -L "https://get.daocloud.io/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 3. 启动所有容器
echo "启动所有服务..."
docker compose down  # 先停止旧服务
docker compose up -d --build  # 重新构建并启动

# 4. 检查服务是否启动成功
echo "检查容器状态..."
docker compose ps

echo -e "\n==================== 部署完成！===================="
echo "访问地址：http://$(hostname -I | awk '{print $1}')"
