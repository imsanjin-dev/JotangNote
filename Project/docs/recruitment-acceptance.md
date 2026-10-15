# 2026 焦糖后端招新交付检查（2026-10-14）

对照招新网站原文的后端启蒙篇、入门篇、进阶篇进行检查。本表区分代码实现、实测、文档截图和最终网站提交，不能代替评审结论。

## 各阶段对照

| 阶段/任务 | 已有内容 | 剩余问题 |
| --- | --- | --- |
| 启蒙：Hello World、FastAPI | Notes/01-Environment，有真实终端和浏览器截图 | 已具备必需基本证据 |
| 启蒙：MySQL、Redis、RabbitMQ、AI Agent、HTTP/API/JSON/HTTPS 基础 | Notes/02 至 Notes/09 均有 Markdown 学习笔记 | 评审时仍须能够用自己的话解释 |
| 入门 Part 1：笔记 CRUD、MySQL、注册登录、作者权限 | app.py、authentication.md、test_auth.py；既有用户实测与模拟测试 | 功能流程截图缺失 |
| 入门 Part 2：Redis 缓存 | note_cache.py、redis-cache.md、test_cache.py；真实缓存联调 | 缓存命中/失效截图缺失 |
| 入门 Part 3：RabbitMQ 异步新增、修改、删除 | note_queue.py、note_worker.py、rabbitmq-async.md、test_async.py；真实任务验收 | 202 入队、任务 completed、Worker 执行结果截图缺失；启动须使用 NOTE_WRITE_MODE=async |
| 进阶 Part 1：AI /chat | ai_client.py；真实 YosHub DeepSeek 调用成功 | 已登录聊天流程截图缺失 |
| 进阶 Part 2：会话历史 | chat_session.py；真实模型多轮追问验证 | 操作流程截图缺失 |
| 进阶 Part 3：笔记 ID 工具调用、工具消息进入上下文 | ai_client.py、ai-agent.md、test_chat_advanced.py；真实模型 + 合成笔记回调通过 | 用真实数据库的无敏感测试笔记演示并截图更有说服力 |
| 进阶 Part 4：Agent 编写前端 | Project/web/index.html 和未登录网页真实截图 | 用户确认网页可用，但仍缺已登录笔记和 AI 聊天操作截图 |

总计自动化测试 46/46 通过，仓库 GitHub public。截图当前仅有两张启蒙篇 Hello World 和一张未登录前端。官方明确要求入门、进阶各功能文档附使用流程必要截图、核心逻辑与个人说明、测试过程与结果；因此不能宣布交付材料全部合格。

## 真实 HTTP 回归检查（2026-10-15 新增辅助脚本）

`Project/scripts/live_acceptance.py` 用于在**已启动的真实 API、MySQL、Redis 以及异步模式下的 RabbitMQ Worker** 上检查一条临时笔记的完整生命周期；脚本新增后已做语法检查和 `--help` 检查，**尚未在带数据库密码的在线 API 上实际运行**。原有自动化测试已重新执行，46/46 通过，二者不能混淆。

在 Ubuntu 项目目录中启动 API / Worker（详见各自文档），再在一个交互式终端运行：

```bash
.venv/bin/python Project/scripts/live_acceptance.py
```

- 输入已有测试用户名和密码（`getpass` 隐藏输入），脚本不会输出 JWT/密码。
- 它验证真实登录、未授权写入 401、创建、数据库回读、Redis 首次写入及命中、修改后缓存失效、删除后 404；自动兼容同步 HTTP 200/201 与异步 202 → Worker completed。
- 默认在结束时删除**脚本新建的临时笔记**，不会删除其他笔记。为网页/AI 笔记工具截图可添加 `--keep-note`，脚本打印测试笔记 ID，**截图完成后需手动删除**。
- 它不会测试跨账户 403、真实 AI 上游调用或截图本身，以上仍需通过 Swagger / 网页单独留证；不能把脚本语法检查说成真实联调已通过。
- 截图和日志中的密码、Bearer Token、私有密钥、个人笔记正文必须打码或完全避开，优先使用临时测试笔记。

## 截图与最终提交清单

1. 注册/登录、笔记 CRUD 及跨账号禁止修改/删除，隐藏口令和 JWT。
2. Redis 首次加载与缓存命中，成功修改/删除后的缓存失效。
3. RabbitMQ 接口 HTTP 202、任务 status=completed 与 Worker 结果。
4. 网页已登录画面、普通聊天、多轮对话、按 ID 读取无隐私测试笔记的 AI 最终回复。
5. 将截图分别嵌入 authentication.md、redis-cache.md、rabbitmq-async.md、ai-agent.md；修正任何与实测冲突的描述。确保自己能解释 AI 辅助完成的核心逻辑。

截至此次核对，LifeOS 记录基础入门五个模块于 10 月 6 日提交；后端启蒙篇 10 月 10 日已在网站提交，尚无评审结果。**没有后端入门篇及进阶篇在招新网站提交完成的明确记录**。GitHub 推送不能替代该动作。

后端启蒙篇官方截止：**2026-10-16 23:59**；后端入门篇及进阶篇：**2026-10-18 23:59**。评论、Docker、搜索、会话持久化、严格幂等与消息顺序保证等属于加分题，不要求全部完成。
