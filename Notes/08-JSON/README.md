# Part 3 基础知识 — JSON

## 1. JSON 是什么？

JSON（JavaScript Object Notation）是一种常用的文本数据交换格式，特别适合前后端传递结构化数据。

前端和后端可能使用不同的编程语言，但都可以按照 JSON 规则对数据进行序列化和解析。例如，JotangNote 的后端可以用 Python 生成 JSON 响应，浏览器用 JavaScript 读取。

JSON 是数据格式，不是 Python 的 `dict` 类型；只是两者结构较为接近。

## 2. JSON 数据长什么样？

一个笔记对象可以表示为：

```json
{
  "id": 5,
  "title": "Redis笔记",
  "content": "学习String和Hash",
  "is_public": false,
  "tags": ["Redis", "后端"],
  "deleted_at": null
}
```

JSON 常见数据类型及 Python 对应关系：

| JSON | Python |
| --- | --- |
| 对象 `{}` | `dict` |
| 数组 `[]` | `list` |
| 字符串 | `str` |
| 数字 | `int` / `float` |
| `true`、`false` | `True`、`False` |
| `null` | `None` |

JSON 对象中的键必须使用双引号包围，字符串也必须使用双引号。JSON 不支持普通语法里的注释或尾随逗号。

## 3. Python 对象怎样转为 JSON？

Python 内置 `json` 模块。

### 序列化：Python 对象 → JSON 字符串

```python
import json

note = {
    "id": 5,
    "title": "Redis笔记",
    "is_public": False
}

json_str = json.dumps(note, ensure_ascii=False)
print(json_str)
```

`json.dumps()` 返回字符串（`str`）；`ensure_ascii=False` 可以让中文直接保留为可读文字。

### 反序列化：JSON 字符串 → Python 对象

```python
data = '{"id": 5, "tags": ["Redis", "MySQL"]}'
note = json.loads(data)

print(type(note))          # <class 'dict'>
print(type(note["tags"]))  # <class 'list'>
```

`json.loads()` 负责解析文本。实际结果类型由 JSON 最外层的值决定：对象得到 `dict`，数组得到 `list`，其他合法 JSON 值也可以是字符串、数字、布尔值或 `None`。

注意 `dumps` 和 `loads` 中的 `s` 对应字符串操作；`dump` 和 `load` 也有针对文件对象的形式。

## 4. JSON 如何用于 FastAPI？

例如路由返回：

```python
@app.get("/notes/example")
def example_note():
    return {
        "id": 5,
        "title": "Redis笔记",
        "is_public": False
    }
```

FastAPI 通常会将可序列化的返回值编码为 JSON 响应。对请求中的 JSON，框架可以结合 Pydantic 数据模型完成解析和数据校验。

实际接口使用时还需要注意：

- 请求体的 `Content-Type` 通常是 `application/json`；
- JSON 的 `false` 对应 Python 的 `False`，而不能直接把 JSON 语法当成 Python 语法；
- 日期时间和自定义对象等不一定能直接由标准库 `json.dumps()` 处理，可能需要先转换成 JSON 支持的类型。

## 5. 本阶段理解与实践情况

已能判断 JSON 对象对应 Python `dict`，JSON 数组对应 `list`，并能正确解释 `json.loads()` 解析嵌套对象和数组后的类型。理解使用 `json.dumps()` 和 `json.loads()` 在 Python 对象与 JSON 字符串间转换。

本节是概念与示例学习，没有在项目中单独执行新的 JSON 测试；后续实际开发 API 时继续应用。

## AI 使用说明

使用 ChatGPT 解释 JSON 数据类型、Python 序列化和 FastAPI 中的 JSON 响应，协助整理学习笔记；本节新增示例未做独立运行验收。
