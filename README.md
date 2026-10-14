# JotangNote

2026 焦糖工作室后端方向招新项目，主要使用 **Python + FastAPI**，开发和学习环境为 Ubuntu 虚拟机及 PyCharm Remote Development。

## 当前进度

- **启蒙篇 Part 1：** 已完成终端 Hello World、FastAPI `GET /hello`，保存运行截图。
- **启蒙篇 Part 2：** 已完成 MySQL、Redis、RabbitMQ、AI Agent 的基础知识学习与笔记；RabbitMQ 另外完成 Docker + Pika 最小消息收发练习。
- **启蒙篇 Part 3：** 已整理 HTTP、API、JSON、HTTPS 笔记。
- **入门篇：** 笔记 CRUD、注册/登录已实现；JWT 和作者权限通过 8 项自动化模拟测试。Redis 查询缓存代码已实现，新增模拟测试 8 项及真实 MySQL + Redis 查询链路 9 项均通过；用户授权 PUT/DELETE 与异步写入的主要数据库联调此前已通过。RabbitMQ 笔记异步接口与 Worker 已实现（默认同步模式防止未启动消息队列时破坏旧接口）；RabbitMQ 服务端已安装，真实异步新增、修改、删除均已完成 MQ + MySQL + Redis 联调。
- **进阶篇：** 已实现多轮会话、笔记查询 Tool Use 和前端工作台；46/46 项自动化测试通过。已按 YosHub 文档配置本地 OpenAI 兼容接口，但尚未提供自己的 API Key，因此未进行真实上游联调。

## 项目结构

- [Notes/](Notes/README.md)：启蒙篇学习笔记、截图和练习记录。
- [Project/src/](Project/src/)：已编写的 Python 源码，包括 Hello World、FastAPI 和 RabbitMQ 示例。
- [Project/docs/](Project/docs/)：JWT、Redis、RabbitMQ、AI 接口与进阶 Agent 的说明、测试步骤和网页截图。
- [Project/tests/](Project/tests/)：API 自动化测试。
- [requirements.txt](requirements.txt)：项目依赖；[.python-version](.python-version) 为 Python 版本提示。

## 启蒙篇笔记

1. [开发环境与运行截图](Notes/01-Environment/README.md)
2. [MySQL](Notes/02-MySQL/README.md)
3. [Redis](Notes/03-Redis/README.md)
4. [RabbitMQ](Notes/04-RabbitMQ/README.md)
5. [AI Agent](Notes/05-AI-Agent/README.md)
6. [HTTP 请求与响应](Notes/06-HTTP/README.md)
7. [API 接口设计](Notes/07-API/README.md)
8. [JSON](Notes/08-JSON/README.md)
9. [HTTPS](Notes/09-HTTPS/README.md)

## Python 3.13 开发环境

Ubuntu 22.04 的系统 Python 仍是 3.10，请不要更改 /usr/bin/python3。JotangNote 已改用独立的 Python 3.13.16 虚拟环境。

```bash
cd ~/jotang-recruit/JotangNote
.venv/bin/python --version
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s Project/tests -v
```

旧的 Python 3.10 虚拟环境保留在 .venv-py310-backup，已被 Git 忽略。Python 3.13 由 uv 管理。

启动 API 前需要 JWT_SECRET_KEY（项目根目录 .env，参考 .env.example）；新机器可以用 openssl rand -hex 32 生成新密钥。数据库密码应通过环境变量提供，不要提交真实密码或密钥。

```bash
read -rsp "DB_PASSWORD: " DB_PASSWORD
echo
export DB_PASSWORD
.venv/bin/uvicorn app:app --app-dir Project/src --host 0.0.0.0 --port 8080 --reload
```

通过 http://<虚拟机 IP>:8080/docs 打开 Swagger，登录获取 access_token 后使用 Authorize 按钮授权。细节见 [JWT 认证与作者权限](Project/docs/authentication.md)。

## Redis 缓存

入门篇 Part 2 已接入 Redis 查询缓存；缓存键、TTL、缓存失效与安装联调见 [Redis 缓存实践](Project/docs/redis-cache.md)。Python 客户端与 Redis 服务端均已安装并通过连通性检查；首次在新 Ubuntu 环境部署时仍需按说明安装服务端。

## RabbitMQ 异步操作

可切换异步写入、后台消费者、任务状态查询以及部署流程，见 [RabbitMQ 异步笔记操作](Project/docs/rabbitmq-async.md)。**默认仍为同步写入；此前已经通过 RabbitMQ + Worker + MySQL + Redis 的异步真实链路验收。**

## AI 会话、Tool Use 与网页（进阶篇 Part 1–4）

已经实现需要登录的 `POST /chat`、多轮会话和笔记 Tool Use；上游服务使用项目根目录 `.env` 的 `AI_BASE_URL`、`AI_MODEL`、`AI_API_KEY` 配置。当前准备使用 YosHub OpenAI Chat Completions 兼容接口，详见 [AI Agent / YosHub 配置和测试](Project/docs/ai-agent.md)。尚未配置真实 API Key，不能认为已联通模型服务。

## 网页快速使用

按照上面的命令启动 Uvicorn 后，打开 http://虚拟机IP:8080/ 使用笔记管理与 AI 聊天工作台；也可继续打开 /docs 使用 Swagger。网页无需 Node 或前端构建环境。登录前需在终端设置 DB_PASSWORD；聊天另需在 .env 中自行设置 AI_API_KEY（不要上传密钥）。

网页截图和关键流程见 [进阶篇说明](Project/docs/ai-agent.md)。服务端会话仅在内存保留 30 分钟、最近 10 轮，重启不会保留。在 AI_API_KEY 缺失时聊天返回 503，而非生成虚假结果。

## 验收状态

- 基础笔记 CRUD：用户此前通过 Swagger 实际验收。
- 注册：用户此前确认实际测试可用。
- 登录 JWT、Token 校验与作者权限：自动化模拟测试 8/8 通过；本轮没有重新进行真实 MySQL 身份认证测试。
- Redis 缓存：8 项模拟测试通过；Redis 6.0.16 真实服务的 13 项检查全部通过（MySQL 部分模拟）；随后 9 项真实 FastAPI + MySQL + Redis **查询链路**检查全部通过。授权 PUT/DELETE 后续已由 RabbitMQ 异步路径完成真实联调。
- RabbitMQ 异步代码新增 13 项模拟与异常分支测试，项目合计 29/29 通过；真实异步 POST、PUT、DELETE → Worker → MySQL + Redis 已完成主要功能验收；AI Part 1 `/chat` 已实现但未做真实模型 API 联调，其余进阶功能尚未实现。

启蒙篇运行截图保存在 [环境笔记](Notes/01-Environment/README.md) 中。
