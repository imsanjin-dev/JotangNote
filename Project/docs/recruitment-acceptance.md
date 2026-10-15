# 2026 焦糖后端招新交付检查（更新于 2026-10-15）

对照招新网站原文的后端启蒙篇、入门篇、进阶篇进行检查。本表区分代码实现、实测、文档截图和最终网站提交，不能代替评审结论。

## 各阶段对照

| 阶段/任务 | 当前证据 | 仍需注意 |
| --- | --- | --- |
| 启蒙：Hello World、FastAPI | Notes/01-Environment 两张真实截图 | 启蒙篇已在招新网站提交 |
| 启蒙：MySQL、Redis、RabbitMQ、AI Agent、HTTP/API/JSON/HTTPS | Notes/02–09 学习笔记 | 评审时需用自己的话解释 |
| 入门 Part 1：CRUD、注册登录、作者权限 | authentication.md；网页真实账号登录、笔记新增/读取/修改/删除截图；JWT 权限测试 | 跨用户 403 为自动化验证，未另拍真实跨账号浏览器图 |
| 入门 Part 2：Redis 缓存 | redis-cache.md；实际 GET 后 TTL 290 秒，PUT/DELETE 后缓存失效；相关网页图 | Redis CLI 结果为记录，未另拍终端图 |
| 入门 Part 3：RabbitMQ 异步新增/修改/删除 | rabbitmq-async.md；真实 202、任务 completed、删除及 404；Swagger 截图 | Worker 控制台未另拍，状态和数据库结果已验收 |
| 进阶 Part 1：/chat | ai-agent.md；真实 DeepSeek 已登录网页对话图 | 第三方额度、服务可用性不保证长期稳定 |
| 进阶 Part 2：会话历史 | ai-agent.md；真实多轮追问图和测试 | 当前为内存会话，持久化属于 Bonus |
| 进阶 Part 3：笔记 ID Tool Use | ai-agent.md；真实 MySQL 无隐私测试笔记 ID 5 问答图 | 不把模型文本单独当工具调用审计 |
| 进阶 Part 4：Agent 前端 | Project/web/index.html；真实登录/笔记/AI 聊天截图 | 开发者需要能说明网页与接口的关联 |

**2026-10-15 本轮新验收：** Windows Edge → FastAPI（Ubuntu）→ MySQL/Redis/RabbitMQ Worker/DeepSeek；网页注册登录和笔记 CRUD、真实 AI 多轮及笔记查询，Swagger 异步 HTTP 202 → task completed，并拍摄浏览器操作图。新建的测试笔记 ID 5/6 已删除，GET 均为 404；仅留下无隐私测试账号 `recruit_demo_20261015` 等待日后清理。发现网页 `createBtn` 重复且有一处不完整标签，已做一行最小修复，原有自动化 **46/46** 再次通过。

关键截图统一放在 `Project/docs/assets/jotang-*.png`，按主题分别嵌入 `authentication.md`、`redis-cache.md`、`rabbitmq-async.md`、`ai-agent.md`。截图是真实界面，不含明文密码、JWT、密钥和私人笔记。Swagger 的 Curl 命令区因可能包含 Authorization 而在截图时隐藏。

**当前只剩招新网站的入门篇和进阶篇正式提交，及提交前阅读核对文档与截图。** 若评审特别要求跨账号 403 或 Worker 控制台画面，可另补；不能把本地 GitHub Push 等同网站提交，也不能宣称已获平台审核通过。

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

## 网站提交前最后核对

1. 确认入门篇文档 `authentication.md`、`redis-cache.md`、`rabbitmq-async.md` 中图片可正常显示。
2. 确认进阶篇文档 `ai-agent.md` 的真实 DeepSeek、多轮和 Tool Use 图片可正常显示。
3. 向焦糖招新网站分别提交入门篇、进阶篇所需 GitHub 仓库链接或平台要求内容；必要时按评审要求补证。
4. 不上传 .env、JWT、API Key、数据库密码或截图中的私密数据。

截至此次核对，LifeOS 记录基础入门五个模块于 10 月 6 日提交；后端启蒙篇 10 月 10 日已在网站提交，尚无评审结果。**没有后端入门篇及进阶篇在招新网站提交完成的明确记录**。GitHub 推送不能替代该动作。

后端启蒙篇官方截止：**2026-10-16 23:59**；后端入门篇及进阶篇：**2026-10-18 23:59**。评论、Docker、搜索、会话持久化、严格幂等与消息顺序保证等属于加分题，不要求全部完成。
