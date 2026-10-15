# 招新任务检查

对照焦糖后端启蒙篇、入门篇、进阶篇要求整理。代码、笔记和截图均保存在本仓库中。

| 题目 | 已有内容 |
| --- | --- |
| 启蒙 Part 1 | [终端和 FastAPI Hello World 截图](../../Notes/01-Environment/README.md) |
| 启蒙 Part 2–3 | [MySQL / Redis / RabbitMQ / AI Agent / HTTP / API / JSON / HTTPS 笔记](../../Notes/README.md) |
| 入门 Part 1 | [notes / users、CRUD、注册登录、作者权限与截图](authentication.md) |
| 入门 Part 2 | [Redis 查询缓存、失效处理和测试记录](redis-cache.md) |
| 入门 Part 3 | [RabbitMQ 异步写入、任务状态与 HTTP 202/完成截图](rabbitmq-async.md) |
| 进阶 Part 1 | [AI /chat 接口](ai-chat.md) |
| 进阶 Part 2–3 | [多轮会话、Tool Calling 及真实笔记查询截图](ai-agent.md) |
| 进阶 Part 4 | [网页工作台及已登录截图](ai-agent.md) |

## 测试结果

- `python -m unittest discover -s Project/tests -v`：46 项通过。
- 真实浏览器：注册登录、笔记新增/查询/修改/删除、AI 聊天、多轮追问、根据 ID 查询测试笔记。
- Redis：缓存命中、300 秒 TTL、写操作完成后的缓存失效。
- RabbitMQ：POST 返回 202，随后可查询到任务 `completed`；PUT / DELETE 经 Worker 执行后，数据库与缓存结果正确。
- 测试使用无隐私笔记，截图位于 `Project/docs/assets/`，测试笔记已清理。

## 不属于必做的内容

严格的消息幂等与顺序保障、评论、全文搜索、Docker 部署、AI 会话持久化等属于加分拓展；当前仅实现了主线功能。跨账号修改/删除的 403 由自动化测试验证，本次没有另拍双账号截图。

建表参考见 [schema.sql](../sql/schema.sql)，该文件按代码字段设计，未从既有 MySQL 直接导出。运行前需根据 `.env.example` 配置本机数据库、消息队列和模型服务，不要提交任何真实凭据。
