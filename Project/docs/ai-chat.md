# 进阶篇 Part 1：接入 AI API

`POST /chat` 接收网页提交的问题，调用兼容 Chat Completions 的服务并返回文本。后来又在这个接口上增加了多轮会话和笔记查询工具，当前完整实现见 [会话、Tool Use 和前端](ai-agent.md)。

## 调用流程

1. `app.py` 接收 JSON，请求先经过 JWT 身份认证。
2. `chat_session.py` 取得当前用户的对话历史。
3. `ai_client.py` 组装消息，调用模型服务；需要查询笔记时走工具调用。
4. 只有取得最终回复后才保存本轮上下文，返回 `conversation_id` 和 `reply`。

请求示例（需 Bearer Token）：

~~~json
{"message":"帮我整理笔记 ID 为 5 的内容"}
~~~

回复格式：

~~~json
{"conversation_id":"0123456789abcdef0123456789abcdef","reply":"整理后的内容"}
~~~

上面是接口格式示例。`app.py` 只负责 HTTP、认证和会话衔接；`ai_client.py` 负责与模型通信，这样切换兼容供应商时可以主要改配置，不必重写路由。

AI 上游通过项目 `.env` 中的 `AI_BASE_URL`、`AI_MODEL`、`AI_API_KEY` 配置。无有效 JWT 返回 401；请求参数不合法返回 422；缺少 Key 返回 503；上游请求失败或无有效回复返回 502。

## 测试

`test_chat.py` 覆盖鉴权、普通对话、异常响应；`test_chat_advanced.py` 覆盖会话和工具处理。项目 46 项自动化测试通过。2026-10-15 已在真实网页完成 DeepSeek 聊天、多轮追问和笔记 ID 查询，相关截图见 [会话、Tool Use 和前端](ai-agent.md)。
