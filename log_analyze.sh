#!/bin/bash
###########################################################
# 功能：服务器自动化监控 + 日志分析 + 文件备份一体化脚本
# 包含：主机ping检测、端口监控、CPU/内存/磁盘监控、日志分析、日志清理、文件备份、邮件告警
###########################################################

# ====================== 【1】基础配置（请自行修改） ======================
# 监控目标主机
PING_HOST="127.0.0.1"
# 监控端口（多个用空格隔开）
MONITOR_PORT="80"
# 系统资源阈值（内存使用率%，CPU使用率%，磁盘使用率%）
MEM_THRESHOLD=85
CPU_THRESHOLD=90
DISK_THRESHOLD=85
# 日志文件路径
SYS_LOG="/root/devops-project/logs/access.log"
ERROR_LOG="/root/devops-project/logs/error.log"
# 日志清理天数
LOG_CLEAN_DAY=30
# 备份源目录 & 备份目标目录
BACKUP_SRC="/root/devops-project"
BACKUP_DIR="/home/backup"
# 管理员邮箱
ADMIN_EMAIL="18633130289@163.com"
# 脚本日志
SCRIPT_LOG="/var/log/monitor_script.log"

# ====================== 【2】工具函数 ======================
# 日志输出函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $SCRIPT_LOG
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 邮件发送函数
send_mail() {
    subject="【服务器告警】$1"
    content="$2"
    echo "$content" | mail -s "$subject" $ADMIN_EMAIL
    log "告警邮件已发送：$1"
}

# ====================== 【3】主机状态监控（ping） ======================
ping_check() {
    ping -c 3 -W 2 $PING_HOST > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        msg="主机 $PING_HOST ping 不通！"
        log "ERROR：$msg"
        send_mail "主机失联" "$msg"
    else
        log "主机 $PING_HOST ping 正常"
    fi
}

# ====================== 【4】服务端口监控 ======================
port_check() {
    for port in $MONITOR_PORT; do
        timeout 2 bash -c "echo > /dev/tcp/127.0.0.1/$port" > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            msg="端口 $port 未响应！服务可能异常"
            log "ERROR：$msg"
            send_mail "端口异常" "$msg"
        else
            log "端口 $port 正常"
        fi
    done
}

# ====================== 【5】系统资源监控（CPU/内存/磁盘） ======================
system_check() {
    # 内存使用率
    mem_used=$(free | awk 'NR==2{printf "%.0f", $3/$2*100}')
    # CPU 使用率
    cpu_used=$(top -bn1 | grep load | awk '{printf "%.0f", $(NF-2)*100}')
    # 磁盘根分区使用率
    disk_used=$(df -h / | grep / | awk '{print $5}' | sed 's/%//g')

    log "内存使用率：${mem_used}%，CPU使用率：${cpu_used}%，磁盘使用率：${disk_used}%"

    # 内存告警
    if [ $mem_used -ge $MEM_THRESHOLD ]; then
        msg="内存使用率过高：${mem_used}%，阈值：${MEM_THRESHOLD}%"
        log "ERROR：$msg"
        send_mail "内存告警" "$msg"
    fi

    # CPU告警
    if [ $cpu_used -ge $CPU_THRESHOLD ]; then
        msg="CPU使用率过高：${cpu_used}%，阈值：${CPU_THRESHOLD}%"
        log "ERROR：$msg"
        send_mail "CPU告警" "$msg"
    fi

    # 磁盘告警
    if [ $disk_used -ge $DISK_THRESHOLD ]; then
        msg="磁盘使用率过高：${disk_used}%，阈值：${DISK_THRESHOLD}%"
        log "ERROR：$msg"
        send_mail "磁盘告警" "$msg"
    fi
}

# ====================== 【6】日志分析（错误检测） ======================
log_analysis() {
    log "开始分析系统日志..."
    # 抓取关键字：error, fail, panic, exception, critical
    error_msg=$(tail -n 200 $SYS_LOG | grep -iE 'error|fail|panic|exception|critical' 2>/dev/null)
    if [ -n "$error_msg" ]; then
        echo "$error_msg" > $ERROR_LOG
        msg="系统检测到异常日志，详情查看附件：\n\n$error_msg"
        log "ERROR：发现系统错误日志"
        send_mail "系统日志异常" "$msg"
    else
        log "系统日志正常，无错误信息"
    fi
}

# ====================== 【7】日志定时清理 ======================
log_clean() {
    log "开始清理 ${LOG_CLEAN_DAY} 天前的日志文件..."
    find /var/log -type f -name "*.log" -mtime +$LOG_CLEAN_DAY -delete > /dev/null 2>&1
    find /var/log -type f -name "*.tar.gz" -mtime +$LOG_CLEAN_DAY -delete > /dev/null 2>&1
    log "旧日志清理完成"
}

# ====================== 【8】文件备份（打包压缩） ======================
file_backup() {
    [ ! -d $BACKUP_DIR ] && mkdir -p $BACKUP_DIR
    backup_file="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    log "开始备份目录：$BACKUP_SRC"
    find $BACKUP_SRC -type f | xargs tar -zcvf $backup_file > /dev/null 2>&1
    
    if [ -f $backup_file ]; then
        log "备份成功：$backup_file"
    else
        msg="文件备份失败！"
        log "ERROR：$msg"
        send_mail "备份失败" "$msg"
    fi
}

# ====================== 【9】主函数（总入口） ======================
main() {
    log "==================== 监控脚本开始执行 ===================="
    ping_check
    port_check
    system_check
    log_analysis
    log_clean
    file_backup
    log "==================== 监控脚本执行完成 ===================="
    echo "" >> $SCRIPT_LOG
}

# 执行主程序
main
