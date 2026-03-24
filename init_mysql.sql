-- 1️⃣ 创建数据库，如果已经存在就跳过
CREATE DATABASE IF NOT EXISTS message_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- 2️⃣ 创建用户，如果已经存在就跳过
CREATE USER IF NOT EXISTS 'flask_user'@'%' IDENTIFIED BY 'flask_pass';

-- 3️⃣ 授权用户访问数据库
GRANT ALL PRIVILEGES ON message_db.* TO 'flask_user'@'%';

-- 4️⃣ 刷新权限，使修改立即生效
FLUSH PRIVILEGES;
