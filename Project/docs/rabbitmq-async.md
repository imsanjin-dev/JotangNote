# RabbitMQ 笔记异步操作（入门篇 Part 3）

## 目的和实际行为

原来请求 → FastAPI → MySQL 操作完成 → HTTP 结果。异步版为：

1. 客户端带 Bearer Token 发送 POST/PUT/DELETE；FastAPI 验证身份。
2. 接口创建任务 ID，将任务状态写入 Redis，再通过 RabbitMQ 投递持久化消息。Broker 确认投递后返回 HTTP **202 Accepted**，表示**已入队，不代表数据库操作已成功**。
3. 独立运行的 `note_worker.py` 订阅队列，从消息里读取操作种类、目标笔记及用户 ID，重新从 MySQL 查询用户，调用现有的 CRUD 数据库函数执行实际更改；修改和删除仍会校验作者，成功后失效 Redis 笔记缓存。
4. Worker 记录任务最终结果，然后向 RabbitMQ 发送 ACK。客户端通过 `GET /tasks/{task_id}` 查看自己任务的 `queued / processing / completed / failed` 状态。

采用三个文件：`note_queue.py` 负责创建与发布任务、缓存任务状态；`note_worker.py` 消费执行；`app.py` 中接口复用现有的 `*_db` 函数。没有引入第二套不一致的 SQL。

## Ubuntu 环境和启动

Ubuntu 安装 RabbitMQ 服务端：

```bash
sudo apt update
sudo apt install -y rabbitmq-server
sudo systemctl enable --now rabbitmq-server
sudo systemctl status rabbitmq-server
```

首次安装时创建单独的业务账户：

```bash
cd ~/jotang-recruit/JotangNote
MQ_PASS=$(openssl rand -hex 24)
sudo rabbitmqctl add_user jotang "$MQ_PASS"
sudo rabbitmqctl set_permissions -p / jotang ".*" ".*" ".*"
printf '\nRABBITMQ_USER=jotang\nRABBITMQ_PASSWORD=%s\n' "$MQ_PASS" >> .env
unset MQ_PASS
chmod 600 .env
```

本项目的 API 和 Worker 在同一台虚拟机上，RabbitMQ 不需要对公网开放。如果 `jotang` 用户已存在，应修改其密码，而不是再次执行 `add_user`。

Worker 和 API 分别运行在两个终端。先在 Worker 终端设置数据库密码并启动：

```bash
cd ~/jotang-recruit/JotangNote
read -rsp "DB_PASSWORD: " DB_PASSWORD
echo
export DB_PASSWORD
.venv/bin/python Project/src/note_worker.py
```

另一个终端也需要设置 `DB_PASSWORD`，并在 `.env` 中启用 `NOTE_WRITE_MODE=async`，然后启动 API：

```bash
.venv/bin/uvicorn app:app --app-dir Project/src --host 0.0.0.0 --port 8080
```

修改 `.env` 后应重启 API 和 Worker，使新的配置生效。

## 操作步骤

1. 在 Swagger `/docs` 登录并授权，提交新增笔记请求；接口返回 HTTP 202 和任务 ID。
2. 用 `GET /tasks/{task_id}` 查询任务状态，完成后根据返回的笔记 ID 查询正文。
3. 再分别提交修改和删除，等待任务完成后查询笔记，确认内容更新或返回 404。

## 测试过程

- 先启动 RabbitMQ、Redis、MySQL、Worker 和 FastAPI，设置 `NOTE_WRITE_MODE=async`。
- 在 Swagger 登录并提交笔记新增请求，返回 202 和任务 ID；通过任务状态接口查到 `completed`，再 GET 笔记确认已写入 MySQL。
- 异步修改笔记后，新的内容可查询且对应旧 Redis 缓存被删除；异步删除笔记后，再次查询返回 404。
- `test_async.py` 覆盖任务查询权限、消息发布失败、Worker 错误、ACK 等分支。当前并未实现严格的重复消息幂等保证，这部分属于加分项。

## 异步操作截图（2026-10-15）

在 Swagger 中新建测试笔记，请求返回 **202 Accepted** 和任务 ID，表示操作已入队。

![RabbitMQ 写请求返回 HTTP 202 和任务 ID](assets/jotang-async-202.png)

随后查询任务状态，返回 `completed` 和新笔记 ID，确认 Worker 已完成写入。

![查询 RabbitMQ 任务完成状态](assets/jotang-async-completed.png)

再提交异步删除；任务完成后查询笔记返回 404，对应的 Redis 缓存键已清除。

![Swagger 异步 DELETE 接口提交结果](assets/jotang-async-delete.png)

截图未显示登录 Token。严格幂等和故障恢复等加分内容尚未实现。

## 技术与边界

- `queue_declare(..., durable=True)` 使队列元数据重启后保留；`delivery_mode=2` 请求消息持久化；`confirm_delivery()` + `mandatory=True` 检查 Broker 是否确认接收消息。
- `basic_qos(prefetch_count=1)` 和单个 Worker 将未确认消息限制为一条，降低乱序风险；`auto_ack=False` 与执行后 `basic_ack` 让消息在处理前不会自动删除。
- Redis 的 `jotang:task:<id>` 仅保存进度与结果，TTL 为一天，不是永久任务历史；原有 `jotang:note:<id>` 保存的是笔记查询缓存，两者分开。
- **可靠性限制：** 当前是招新教学实现，并不保证严格的 exactly-once：Worker 在 MySQL commit 后、保存完成状态/ACK 前崩溃时 RabbitMQ 可能重投递，尤其是 create 有重复创建风险；若 MySQL 已成功而 Redis 状态更新失败，也可能让状态滞留在 processing。当前代码会记录日志并避免因完成状态写入失败而主动再次执行数据库写入。生产设计需增加 MySQL 任务表/唯一任务 ID、事务内幂等检查、持久化结果与故障恢复。题面将顺序性与幂等性强化列为加分项，这里暂不声称已完成。
- `NOTE_WRITE_MODE=async` 启用 RabbitMQ 写入；未设置时默认同步写数据库。该开关在服务端配置，不由客户端指定。
