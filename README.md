# JotangNote

2026 焦糖工作室后端方向招新项目，主要使用 **Python + FastAPI**，开发和学习环境为 Ubuntu 虚拟机及 PyCharm Remote Development。

## 当前进度

- **启蒙篇 Part 1：** 已完成终端 Hello World、FastAPI `GET /hello`，保存运行截图。
- **启蒙篇 Part 2：** 已完成 MySQL、Redis、RabbitMQ、AI Agent 的基础知识学习与笔记；RabbitMQ 另外完成 Docker + Pika 最小消息收发练习。
- **启蒙篇 Part 3：** 已整理 HTTP、API、JSON、HTTPS 笔记。
- **入门篇与进阶篇：** 尚未完成。笔记中的 `/notes` 和 Agent 功能为设计示例，不表示已经实现。

## 项目结构

- [Notes/](Notes/README.md)：启蒙篇学习笔记、截图和练习记录。
- [Project/src/](Project/src/)：已编写的 Python 源码，包括 Hello World、FastAPI 和 RabbitMQ 示例。
- [Project/docs/](Project/docs/)：后续项目文档目录。

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

## Part 1 最小运行示例

在安装好所需 Python 依赖的环境下：

```bash
python Project/src/hello.py
cd Project/src
uvicorn app:app --host 0.0.0.0 --port 8080
```

启动 FastAPI 后可通过 `GET /hello` 访问示例接口。若从虚拟机外浏览器访问，需要使用该虚拟机实际 IP 地址，而不是宿主机的 `localhost`。两项运行结果截图保存在 [环境笔记](Notes/01-Environment/README.md) 中。

本仓库为学习项目。除已明确记录的练习外，笔记中的 Python/Redis、MySQL、Agent 和笔记 CRUD 等示例均不视为已完成运行验收。
