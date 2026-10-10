# Part 3 基础知识 — API 接口设计

## 1. API 是什么？

API（Application Programming Interface，应用程序编程接口）是程序之间交互的约定。API 不仅限于 Web；在 JotangNote 中，我们主要使用通过 HTTP 调用的 Web API。

例如，前端需要显示一篇笔记，就向后端请求 `GET /notes/5`；后端根据路由、参数和用户权限查询数据库，再返回结果。

设计 HTTP API 通常需要考虑：**请求方法、URL 路径、参数、返回的数据格式、身份权限和失败情况**。

## 2. 如何设计获取笔记详情的 API？

假设需要获取 ID 为 5 的笔记：

```http
GET /notes/5 HTTP/1.1
Host: localhost:8080
Accept: application/json

```

- **请求方法**：`GET`，用于读取资源；
- **路径**：`/notes/5`，其中 `5` 是笔记 ID；
- **权限**：确认用户能否访问这篇笔记；
- **响应**：通常返回笔记 ID、标题、正文、作者、创建和修改时间等。

一种可能的 JSON 响应（仅供设计说明）：

```json
{
  "id": 5,
  "title": "Redis学习笔记",
  "content": "学习String和Hash",
  "author": {
    "id": 12,
    "name": "golds"
  },
  "created_at": "2026-10-10T10:00:00Z",
  "updated_at": "2026-10-10T11:00:00Z",
  "images": ["/media/redis.png"],
  "like_count": 25,
  "favorite_count": 8,
  "comment_count": 12
}
```

其中图片通常只返回访问 URL，不必把整个媒体文件嵌入 JSON。点赞、收藏、评论计数属于以后按实际产品需求选择的扩展字段，不表示当前项目已实现社交功能。

## 3. 评论为什么适合单独做接口？

一篇笔记可能有很多评论，详情接口没必要一次返回所有评论。可以另外提供：

```http
GET /notes/5/comments?limit=20&offset=0
```

这表示分批获取评论，而不是一次性加载全部数据。

这里的 `limit`、`offset` 是 URL 查询参数（Query Parameters），`5` 是路径参数（Path Parameter）。`offset` 分页只是常见方案之一；真实系统也可以根据场景使用游标分页。

## 4. 身份认证与权限控制

假设笔记是私人笔记，后端不能因为客户端知道笔记 ID 就允许读取。一般需要：

1. 验证用户身份；
2. 查询笔记及其可见性、所属用户；
3. 判断当前用户是否拥有访问权限；
4. 在允许访问时返回内容，否则拒绝。

常见状态码：

- **401**：用户未通过身份认证；
- **403**：已识别身份，但无权访问；
- **404**：资源不存在，也可用来隐藏私人笔记的存在性。

如果选择对无权访问私人笔记的用户返回 404，后端必须真正禁止返回受保护的内容，而不是仅改变提示文字。

## 5. FastAPI 中怎样定义接口？

下面是说明接口结构的示意代码：

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/notes/{note_id}")
def get_note(note_id: int):
    note = find_note(note_id)  # 示意函数，尚未实现
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
```

`note_id: int` 表示期望的路径参数类型。实际实现还要补充数据库访问、用户认证、笔记权限检查及响应数据校验。

## 6. 本阶段理解与实践情况

通过设计讨论，已能为查询笔记选择 GET、为删除笔记选择 DELETE、为仅修改标题选择 PATCH；能够提出笔记详情应返回标题、正文、作者、时间和媒体等信息，并理解评论分页及私人笔记的权限校验。

**本阶段是 API 设计学习，没有把以上 `/notes` 系列接口实现到 JotangNote 中。** 后续入门篇再编写真正的 CRUD 接口。

## AI 使用说明

使用 ChatGPT 对 API 需求拆分、字段选择、分页与权限控制进行讲解和整理；本节示例是方案，不作为已经运行的后端功能。
