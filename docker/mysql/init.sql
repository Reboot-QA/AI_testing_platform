-- 首次初始化数据卷时确保库存在（MYSQL_DATABASE 通常已创建，此处作兜底）
CREATE DATABASE IF NOT EXISTS ai_testcase CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
