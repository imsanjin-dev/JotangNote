# Part 3 基础知识 — HTTP 请求与响应

## 1. HTTP 是什么？

HTTP（Hypertext Transfer Protocol，超文本传输协议）定义了客户端和服务器交换请求、响应的规则。

在 JotangNote 中，浏览器是客户端，运行 FastAPI 的程序是后端服务器。客户端请求获取或修改笔记，服务器根据请求执行相应操作，然后返回响应。

基本流程：

```text
浏览器 → HTTP Request → 后端
浏览器 ← HTTP Response ← 后端
```

HTTP 负责规定通信内容的语义；实际传输还依赖下层网络协议。HTTPS 是在 HTTP 通信外增加 TLS 安全保护。

## 2. HTTP 请求和响应由哪些部分构成？

### 请求（Request）

以 HTTP/1.1 的文本形式为例：

```http
GET /notes/5 HTTP/1.1
Host: localhost:8080
Accept: application/json

```

- **请求行**：方法（GET）、请求目标（`/notes/5`）、协议版本；
- **请求头（Headers）**：例如 `Host`、`Accept`、`Content-Type`，表示目标主机、期望内容格式等；
- **请求体（Body）**：可选，适合提交笔记正文等内容。

例如创建笔记的请求可写作（省略了部分传输相关请求头）：

```http
POST /notes HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "title": "Redis笔记",
  "content": "学习String和Hash"
}
```

### 响应（Response）

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 5,
  "title": "Redis笔记"
}
```

- **状态行**：协议版本、状态码和说明短语；
- **响应头**：告知返回数据类型等信息；
- **响应体**：实际返回的文本或 JSON 数据。

HTTP/2、HTTP/3 的底层消息编码形式与上面的 HTTP/1.1 文本形式不同，但仍保留方法、目标、状态、头字段和内容等核心概念。

## 3. GET、POST、PUT、PATCH、DELETE 的区别

| 方法 | 常见用途 | JotangNote 示例 |
| --- | --- | --- |
| `GET` | 获取资源 | `GET /notes/5` 查询笔记 |
| `POST` | 提交数据，常用于创建 | `POST /notes` 创建笔记 |
| `PUT` | 替换指定资源的状态 | `PUT /notes/5` 提交完整修改后的笔记 |
| `PATCH` | 对资源作部分修改 | `PATCH /notes/5` 只修改标题 |
| `DELETE` | 删除资源 | `DELETE /notes/5` 删除笔记 |

用户提交一篇很长的新笔记，应优先使用 **POST** 并把内容放进请求体，而不是拼接到 GET 的 URL 参数里。

原因是：GET 按协议语义用于获取信息，不应用来执行创建操作；URL 中的大量正文不方便处理，还可能被浏览器历史、服务器日志等记录，带来内容暴露风险。URL 长度限制取决于不同软件的实现，没有适用于所有情况的固定值。

**幂等性**指重复执行同样操作，与执行一次对资源的预期最终效果一致。GET、PUT、DELETE 按规范属于幂等方法；POST 通常不保证幂等；PATCH 也不一定幂等，例如“计数加一”。

## 4. HTTP 状态码

| 状态码 | 含义 | 使用场景 |
| --- | --- | --- |
| `200 OK` | 请求成功 | 读取笔记成功 |
| `201 Created` | 资源已创建 | 成功新增笔记 |
| `202 Accepted` | 请求已接受，但未必执行完 | 异步摘要任务入队 |
| `400 Bad Request` | 请求存在问题 | 客户端提交不符合约定的请求 |
| `401 Unauthorized` | 未通过身份认证 | 未登录或认证凭证无效 |
| `403 Forbidden` | 已拒绝访问 | 当前身份无权访问资源 |
| `404 Not Found` | 找不到资源 | 笔记不存在；也可用于隐藏私人笔记是否存在 |
| `405 Method Not Allowed` | 路径存在，但不支持请求方法 | 只定义了 `GET /hello`，却请求 `POST /hello` |
| `422 Unprocessable Content` | 内容可理解，但无法按要求处理 | FastAPI 请求数据验证失败时的常见默认响应 |
| `500 Internal Server Error` | 服务器内部错误 | 未处理的程序异常 |

注意：找不到笔记是预期内的业务情况，不等于服务器发生 500 错误。405 响应应有 `Allow` 响应头告知允许的方法。

## 5. HTTP 请求如何进入 FastAPI？

访问之前写过的 `/hello` 时：

```text
浏览器请求 /hello
      ↓
Uvicorn 接收网络上的 HTTP 请求
      ↓
通过 ASGI 交给 FastAPI 应用
      ↓
FastAPI 匹配请求方法与路径
      ↓
执行对应的 Python 路由函数
      ↓
返回 HTTP 响应
```

路由示例：

```python
@app.get("/hello")
def hello():
    return {"message": "Hello World!"}
```

`@app.get("/hello")` 只注册 GET 方法；若调用 `POST /hello` 而没有对应路由，通常得到 405。

## 6. 本阶段理解与实践情况

已经在此前的 FastAPI 环境练习中启动 Uvicorn，并通过浏览器访问 `/hello`。本阶段通过问答理解了请求/响应结构、方法语义、常见状态码和幂等性，能区分不存在资源的 404 与方法不允许的 405，知道长篇笔记应通过 POST 请求体提交。

本文中 JotangNote 的 `/notes` 系列路径为接口设计示例，尚未在项目中实现。

## AI 使用说明

使用 ChatGPT 对照启蒙篇问题讲解、问答和整理 HTTP 笔记；示例 `/notes` 请求没有作为已运行接口验收。
