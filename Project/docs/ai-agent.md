# 进阶篇 Part 2–4：会话管理、Tool Use 与网页

> 截至 2026-10-15：46 项自动化测试通过；除 10 月 14 日真实 YosHub DeepSeek 接口联调外，现已完成浏览器真实账号登录、实际 MySQL 笔记读取、多轮聊天及 AI Tool Use，并留下截图。文中 10 月 14 日的「尚未真实网页登录」属于当时历史验收边界，已被以下实测补齐。

## 使用流程

1. 启动 FastAPI，浏览器打开 http://虚拟机IP:8080/。注册或登录后，JWT 由浏览器在本次会话中保存。
2. 页面可根据 ID 查询笔记，或新建、修改、删除笔记；异步写入时会查询任务状态。
3. 在 AI 助手输入问题，首次 POST /chat 只传 message；服务端生成 conversation_id 并返回 reply。
4. 后续 POST /chat 同时传入 message 和前一次返回的 conversation_id，实现追问。点击“新对话”清空网页中的会话 ID。
5. AI 若需查询笔记，自动触发 get_note_by_id 工具；用户只会看到最终自然语言回复。

~~~text
POST /chat + JWT
  → 会话仓库按 user_id 找到历史
  → system + history + user → AI API
     ├─ 直接答复 → 完整轮次入内存 → reply
     └─ tool_calls → 校验 note_id → Redis/MySQL 读取
                     → assistant 调用记录 + tool 结果入上下文
                     → 再次请求 AI → 最终 reply
~~~

![JotangNote 前端工作台实际加载](assets/frontend-workspace.png)

这是用 Windows Edge 浏览虚拟机 FastAPI 网站生成的 1440×900 截图，展示的是未登录首页。它仅证明前端可以加载，不证明真实账户、数据库写入或第三方 AI 对话已联通。

## 2026-10-15 真实已登录网页与 DeepSeek 截图

在 Windows Edge 真实访问 Ubuntu JotangNote：用单独注册的无隐私演示账号登录后，先做两轮问答，第二轮要求「把你刚才的回答改写成两条简短要点」，DeepSeek 返回与上一轮相呼应的两点；随后明确请求模型通过 `get_note_by_id` 读取**真实 MySQL 测试笔记 ID 5**，模型准确列出笔记原文包含的 MySQL、Redis、RabbitMQ 和 AI 按 ID 查询四项技术。这比 10 月 14 日只向合成回调读取模拟笔记更接近实际用户操作。

![真实用户登录后的工作台](assets/jotang-logged-in.png)

![DeepSeek 普通聊天与多轮追问](assets/jotang-chat-multiturn.png)

![DeepSeek 根据真实笔记 ID 读取内容并作答](assets/jotang-ai-tool-use.png)

测试笔记 ID 5 在截图保存后已由原账号删除，`GET /notes/5` 返回 404；截图中的用户与笔记均为专门创建的测试数据。**截图展示用户问答及真实笔记结果；服务端 Tool Call 的消息与工具结果保存逻辑仍以代码、此前独立 SDK 联调及自动化测试共同佐证**，不把最终模型文本单独当成后台函数调用的完整审计证明。

## 接口示例

首次请求，需发送 Bearer JWT：

~~~json
{"message":"总结笔记 ID 为 5 的内容"}
~~~

成功响应结构：

~~~json
{"conversation_id":"0123456789abcdef0123456789abcdef","reply":"模型最终回答"}
~~~

再次请求：

~~~json
{"message":"把刚才的总结改成三点","conversation_id":"0123456789abcdef0123456789abcdef"}
~~~

上面只是接口格式示例，不是实际模型回复。

## 核心实现及设计原因

- Project/src/app.py：仍使用同一个 POST /chat。先从 JWT 获得当前 user_id，检查会话归属，然后串行执行一次聊天请求；只有生成最终回复才提交这轮历史。
- Project/src/chat_session.py：会话字典以随机 32 位会话 ID 为键，只让创建者访问。每一轮单独保存用户消息、AI 工具调用、工具结果和最终回复；按完整轮次裁剪，避免只留下没有配对 tool_calls 的 tool 结果。保留最近 10 轮，30 分钟闲置后过期，最多 200 个会话。重启后内存丢失，持久化属于 Bonus。
- Project/src/ai_client.py：请求携带 get_note_by_id 的 JSON Schema，让模型知道可调用的唯一工具。服务端校验工具名与正整数 note_id，仅执行已有的只读 get_note；附加 assistant tool_calls 和包含 tool_call_id 的工具结果后，再交给模型继续回答。错误参数和不存在的笔记给模型结构化错误；设置最多 4 次工具回合，避免无限循环。
- Project/web/index.html：无额外前端构建依赖。使用 fetch 调用 HTTP API，通过 textContent 安全展示笔记与回复，不执行笔记中的 HTML。JWT 由 sessionStorage 保留在当前浏览器会话，AI_API_KEY 只在服务器环境变量，不会写入网页。

AI 工具只读公开笔记，不提供删除、修改、执行命令等工具。来自笔记的数据是不可信的模型上下文，不应当作为新的系统指令。

## YosHub 中转站配置（2026-10-14）

JotangNote 使用 OpenAI Python SDK 的 Chat Completions 协议（client.chat.completions.create），而不是 Anthropic Messages 或 Responses 协议。根据 https://docx.yoshub.com/：

~~~ini
AI_BASE_URL=https://api2.yoshub.com/v1
AI_MODEL=deepseek-v4.1-flash
AI_API_KEY=你自己的YosHub令牌
~~~

最终请求地址为 https://api2.yoshub.com/v1/chat/completions 。当前选用 DeepSeek V4.1 Flash。**2026-10-14 已使用 YosHub 真实令牌调用 deepseek-v4.1-flash 成功**，完成普通 Chat Completions（模型回复 OK）及真实 Tool Calling（模型主动请求 get_note_by_id）的实测。因此 deepseek-v4.1-flash 是本次接入的可用中转模型 ID；中转站定价、剩余额度及长期稳定性仍需在平台查看。

2026-10-14 用户已自行在本机私有 .env 中设置 AI_API_KEY；虚拟机实际对 YosHub 发起请求并成功得到 OK，首个 SDK 请求计 65 tokens。此前无密钥访问 /v1/models 返回 HTTP 401，仅作为网络和鉴权区别的记录；实际用 Key 调用已通过。

AI Key 仅保留于本机 .env，修改配置后须重启 FastAPI。YosHub 为第三方中转站，聊天内容和自动读取的笔记全文会发送到它及可能的上游；已使用合成的、不包含隐私的测试笔记验证模型工具能力。真实数据库笔记/网页账号流程仍需额外验收。

## 测试与现有限制

2026-10-14 实测：

~~~bash
.venv/bin/python -m unittest discover -s Project/tests -q
.venv/bin/python -m compileall -q Project/src Project/tests
~~~

测试合计 46/46 通过（原有 35、新增 11）。覆盖两轮历史、跨用户会话拒绝、非法会话 ID、工具查笔记全文、工具调用与结果保留、非法工具或参数拒绝、笔记不存在、上游异常不污染历史、轮次裁剪、工具调用次数上限、网页 HTTP 返回。这 46 项自动化测试主要使用模拟上游；另外已独立完成真实 DeepSeek 模型调用（下文），不能把模拟测试和真实联调混为一谈。

独立 Uvicorn 启动后检查 GET / 和 GET /docs 均 HTTP 200，Windows Edge 已实际加载页面并截图。

当前本机 .env 有 JWT_SECRET_KEY 与 AI_API_KEY，未写 DB_PASSWORD；已运行的 Uvicorn 8080 进程通过启动环境持有 DB_PASSWORD。真实网页登录、真实账号 JWT 与 MySQL 笔记全链路本轮尚未重新验收；不能将独立的 SDK 或 TestClient 合成笔记测试说成已完成真实浏览器登录。


### 真实上游与接口验证（2026-10-14）

- 使用项目 .venv 的 OpenAI Python SDK 与本机私有配置，真实请求 YosHub 的 DeepSeek Chat Completions：成功回复 OK；首个诊断请求计 65 tokens，验证了 API Key、模型 ID 和网络。
- 运行真实 ai_client.chat_with_history，注入合成笔记读取回调（未访问 MySQL）：DeepSeek 主动调用 get_note_by_id(7)，成功读取仅存在于合成笔记正文的随机口令；下一轮追问正确回忆。首轮 10.44 秒，追问 6.46 秒。
- 使用真实 FastAPI /chat 路由（TestClient）和真实 YosHub DeepSeek，合成 JWT 用户依赖及内存笔记回调：HTTP 200、返回 32 位会话 ID、工具正常返回笔记口令；跨用户重用该会话 ID 返回 404。
- 正在运行的 Uvicorn 对 GET /、GET /docs、GET /openapi.json 均为 HTTP 200；本机 TCP 3306、6379、5672 可连通，不直接证明数据库登录和网页交互正常。
- 本轮未在实际 MySQL 注册测试用户、创建真实笔记或做真实网页登录，因此尚未完成全部浏览器到数据库的端到端验收。密钥未写入 Git、日志、截图或本文件。

可选会话持久化、评论、全文搜索等 Bonus 未实现。
