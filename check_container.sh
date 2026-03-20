#!/bin/bash
# 容器健康检查 + 异常自动重启

# 要检查的容器列表
CONTAINERS=("devops-nginx" "devops-backend" "devops-redis" "devops-mysql")

for name in "${CONTAINERS[@]}"; do
    # 判断容器是否运行
    if ! docker ps --filter "name=$name" --filter "status=running" | grep -q "$name"; then
        echo "【异常】$name 已停止，正在重启..."
        docker start $name
    else
        echo "【正常】$name 运行中"
    fi
done

echo "巡检完成：$(date)" >> check_log.txt
