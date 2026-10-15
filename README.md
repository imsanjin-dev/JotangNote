# JotangNote

焦糖工作室 2026 后端方向招新项目。我用 Python + FastAPI 实现笔记管理，接入 MySQL、Redis、RabbitMQ，并扩展了 AI 对话和笔记查询。开发环境为 Ubuntu 虚拟机，使用 VS Code / PyCharm。

## 项目功能

| 阶段 | 内容 | 代码与文档 |
| --- | --- | --- |
| 启蒙篇 | Hello World、FastAPI；MySQL、Redis、RabbitMQ、AI Agent、HTTP、API、JSON、HTTPS 学习笔记 | [Notes](Notes/README.md) |
| 入门篇 Part 1 | 笔记 CRUD、用户注册登录、JWT 与作者权限 | [认证和笔记操作](Project/docs/authentication.md) |
| 入门篇 Part 2 | 按 ID 查询时优先读 Redis，未命中再查 MySQL；修改/删除后清除缓存 | [Redis 缓存](Project/docs/redis-cache.md) |
| 入门篇 Part 3 | RabbitMQ 异步处理笔记新增、修改、删除，并查询任务状态 | [RabbitMQ 异步任务](Project/docs/rabbitmq-async.md) |
| 进阶篇 Part 1–4 | `/chat`、多轮会话、查询笔记的 Tool Calling、网页工作台 | [AI 和前端](Project/docs/ai-agent.md) |

## 项目结构

- [Notes](Notes/README.md)：启蒙篇笔记、Hello World 截图和 RabbitMQ 练习
- [Project/src](Project/src)：FastAPI、MySQL、Redis、消息队列、AI 调用和会话管理
- [Project/web](Project/web)：单文件网页
- [Project/docs](Project/docs)：功能说明、关键逻辑和操作截图
- [Project/tests](Project/tests)：自动化测试

## 运行方法

项目在 Ubuntu 22.04 的独立 Python 3.13 虚拟环境中运行。先准备 MySQL 数据库 `jotang_note`、`users` 和 `notes` 表（可参考 [建表 SQL](Project/sql/schema.sql)），以及 Redis、RabbitMQ 服务。建表脚本按当前代码需要的字段整理，**不是现有数据库的结构导出**。参考 [`.env.example`](.env.example) 配置本机的 `.env`；密钥和密码不写入仓库。

~~~bash
cd ~/jotang-recruit/JotangNote
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s Project/tests -v
~~~

启动异步模式需设置 `NOTE_WRITE_MODE=async`，并先运行 Worker：

~~~bash
read -rsp "DB_PASSWORD: " DB_PASSWORD; echo
export DB_PASSWORD
.venv/bin/python Project/src/note_worker.py
~~~

在另一个终端同样导出 `DB_PASSWORD`，然后启动 API：

~~~bash
.venv/bin/uvicorn app:app --app-dir Project/src --host 0.0.0.0 --port 8080
~~~

浏览器访问 `http://虚拟机IP:8080/` 使用工作台，`/docs` 打开 Swagger。异步写入返回 HTTP 202 表示任务已入队，最终是否完成要通过 `GET /tasks/{task_id}` 查询。AI 聊天需要在 `.env` 中自行设置 `AI_BASE_URL`、`AI_MODEL` 和 `AI_API_KEY`。

## 测试结果

2026-10-15 在真实 Ubuntu 服务上用单独的测试账号完成了注册登录、笔记创建/查询/修改/删除、Redis 缓存读写和失效、RabbitMQ 任务状态查询，以及 DeepSeek 多轮聊天和 Tool Calling 查询真实测试笔记。测试笔记已经删除。

项目自动化测试 **46/46 通过**。操作截图见：[启蒙篇](Notes/01-Environment/README.md)、[认证与 CRUD](Project/docs/authentication.md)、[Redis](Project/docs/redis-cache.md)、[RabbitMQ](Project/docs/rabbitmq-async.md)、[AI 聊天与前端](Project/docs/ai-agent.md)。

缓存穿透/击穿的增强方案、严格消息幂等、聊天持久化、全文搜索和 Docker 部署等属于加分方向，本项目没有额外实现。

## 学习记录

从启蒙篇的概念和最小练习开始，逐步把数据库、缓存、异步写入和 AI 对话组合到一个项目中。过程中使用了 AI 辅助答疑、部分代码实现、排错和文档整理。对我来说需要重点理解的是：请求进入路由后怎样访问数据库、事务什么时候提交、异步请求和任务完成有什么区别，以及模型发起 Tool Call 后实际由谁执行查询。
