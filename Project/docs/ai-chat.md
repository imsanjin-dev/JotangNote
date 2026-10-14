# 进阶篇 Part 1：接入 AI 的 /chat 接口

> 这是 Part 1 单轮实现时的阶段记录。2026-10-14 已追加 Part 2–4 的多轮会话、Tool Use 和前端，请查看 [进阶篇最新实现](ai-agent.md)；下方旧阶段说明不代表当前全部能力。**2026-10-14 已通过 YosHub DeepSeek 真实模型调用与 Tool Use 验收**，以最新的 ai-agent.md 为准。

## 实现范围

本阶段只实现**单轮** AI 问答，后续 Part 2 加入会话历史，Part 3 加入笔记 ID 查询 Tool Use，Part 4 用 Agent 辅助开发前端。官方要求的流程截图须在实际 API 联通后再补。

当前新增：

- `POST /chat`：要求 Bearer JWT，JSON 例子：`{"message": "简单介绍一下 JotangNote"}`。
- 成功响应：HTTP 200，JSON `{"reply": "模型回复文本"}`。
- `Project/src/ai_client.py`：由服务端读取 API Key 和模型配置，发送请求，不把密钥发送到浏览器。
- `Project/tests/test_chat.py`：6 项模拟测试，覆盖登录鉴权、输入长度、无 API Key、正常回复、上游错误和空回复。

## 为什么分成两个 Python 文件？

`app.py` 只负责 HTTP 请求的接收、验证 JWT、把 Pydantic `ChatRequest` 中的 `message` 交给调用函数、返回 JSON。

`ai_client.py` 负责构造上游 AI 服务的 HTTP 请求以及解释上游响应。这样替换模型供应商时无需改动 FastAPI 路由逻辑；以后增加会话历史/Tool Use 也有独立的位置。

`OpenAI(...)` 是 **SDK 客户端对象**，不是本机大模型，也不意味着只能使用 OpenAI 的服务。它会通过指定 `base_url` 和 API Key，调用支持 Chat Completions 格式的兼容服务。我们优先采用官方题面推荐的 MiMo：

- Base URL：`https://api.xiaomimimo.com/v1`
- Model 示例：`mimo-v2.6-flash`
- SDK 调用：`client.chat.completions.create(model=..., messages=[...])`
- 上游响应：`completion.choices[0].message.content`

注：MiMo 还支持 Responses API，但当前项目为便于 Part 2/3 的对话消息列表和工具调用，先选 Chat Completions。以服务商当前文档为准。

## 在 Ubuntu 上配置（需用户自己拥有有效 API Key）

打开项目根目录 `.env`，自行添加（请勿把真实 Key 发送给助手、写进 Git 或截图）：

```ini
AI_BASE_URL=https://api.xiaomimimo.com/v1
AI_MODEL=mimo-v2.6-flash
AI_API_KEY=你的真实密钥
```

如使用其他兼容的模型供应商，请同时替换以上配置。此功能可能产生按量计费，调用前应自行确认账户的额度和定价。

安装依赖已完成，代码使用项目 Python 3.13 的 `.venv`，依赖已写入 `requirements.txt`。配置后**需重启 FastAPI**，因为当前服务进程仍是旧代码、且只在加载应用时读取 `.env`。已在运行的 RabbitMQ Worker 不需要为新增 `/chat` 重新部署。

可在 Swagger `/docs` 登录并点击 Authorize，然后使用 `POST /chat`，Body：

```json
{"message": "请用一句话介绍你自己"}
```

## 异常规则

- 401：没有合法的 Bearer 登录凭证。
- 422：消息为空、仅空白或超过 4000 字符。
- 503：服务端没有配置 `AI_API_KEY`。
- 502：AI 上游请求失败或没有返回有效文本；不把上游错误/密钥原样暴露给前端。

HTTP `200` 才表示拿到了模型文本。当前代码没有持久保存聊天，不记忆上次对话，也不能查询笔记；这些分别属于后续 Part 2、Part 3。

## 当前验收证据（2026-10-14）

`test_chat.py` 的 6 项**模拟 API**测试通过，整个项目自动化测试共 **35/35 通过**；`compileall`、`pip check`、`git diff --check` 也通过。

**尚未进行实际 MiMo/其他第三方 AI 服务调用**（当前没有配置 API Key），因此不能声称 Part 1 已完成真实端到端验收。Swagger 截图、真实 API 返回文本、模型计费和网络连通性都尚未验收。
