# JotangNote

2026 焦糖工作室后端方向招新项目，主要使用 **Python + FastAPI**，开发和学习环境为 Ubuntu 虚拟机及 PyCharm Remote Development。

## 当前进度

- **启蒙篇 Part 1：** 已完成终端 Hello World、FastAPI `GET /hello`，保存运行截图。
- **启蒙篇 Part 2：** 已完成 MySQL、Redis、RabbitMQ、AI Agent 的基础知识学习与笔记；RabbitMQ 另外完成 Docker + Pika 最小消息收发练习。
- **启蒙篇 Part 3：** 已整理 HTTP、API、JSON、HTTPS 笔记。
- **入门篇：** 笔记 CRUD、注册/登录已实现；JWT 和作者权限通过 8 项自动化模拟测试，真实 MySQL 联调尚待验收。Redis 缓存、RabbitMQ 笔记异步操作尚未实现。
- **进阶篇：** AI 对话、上下文、Tool Use 和前端仍待完成。

## 项目结构

- [Notes/](Notes/README.md)：启蒙篇学习笔记、截图和练习记录。
- [Project/src/](Project/src/)：已编写的 Python 源码，包括 Hello World、FastAPI 和 RabbitMQ 示例。
- [Project/docs/](Project/docs/)：JWT 登录认证与作者权限的说明和验收步骤。
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

## 验收状态

- 基础笔记 CRUD：用户此前通过 Swagger 实际验收。
- 注册：用户此前确认实际测试可用。
- 登录 JWT、Token 校验与作者权限：自动化模拟测试 8/8 通过，**真实 MySQL 端到端测试尚未验收**。
- Redis、RabbitMQ 后续任务及 AI 进阶功能：尚待完成。

启蒙篇运行截图保存在 [环境笔记](Notes/01-Environment/README.md) 中。
