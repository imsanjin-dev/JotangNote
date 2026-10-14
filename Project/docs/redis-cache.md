# Redis 笔记查询缓存（入门篇 Part 2）

## 目标与实现

`GET /notes/{note_id}` 采用 Cache-Aside（旁路缓存）：

1. 先读取 Redis 键 `jotang:note:{id}`，命中则直接返回。
2. 未命中时查询 MySQL；不存在则返回 404（当前不缓存空结果）。
3. MySQL 查询成功后把笔记转成 JSON 写入 Redis，TTL 为 300 秒，再返回。
4. `PUT` / `DELETE` 仅在 MySQL `commit()` 成功后删除对应缓存键；新建笔记无需删除已有缓存（本项目没有空值缓存）。
5. Redis 连接失败或读写失败时，查询继续回退 MySQL；Redis 缓存不是数据库。

代码位于 `Project/src/note_cache.py` 和 `Project/src/app.py`。缓存 JSON 的日期字段转为 ISO 格式字符串，以保持 FastAPI 实际响应形式一致。

## 环境准备

项目 Python 虚拟环境已安装 `redis==7.4.1`（Python 客户端），**这不等于安装 Redis 服务端**。Ubuntu 若尚无 Redis 服务，请用户亲自执行以下需要 sudo 的命令：

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
```

Redis 仅供本机 API 使用，不要向公网开放 6379 端口。然后无需 sudo 检查：

```bash
redis-cli ping
# 期望：PONG
```

应用默认连接 `redis://127.0.0.1:6379/0`。如需变更，可在项目根目录本地 `.env` 添加 `REDIS_URL=...`；不要提交包含密码的 `.env`。

随后按项目 [README](../../README.md) 中的步骤提供 `DB_PASSWORD` 并启动 Uvicorn（JWT_SECRET_KEY 已从 `.env` 读取）。

## 真实联调建议

1. 用已存在的笔记 ID 请求一次 `GET /notes/{id}`；再请求一次，应命中 Redis。
2. 在 Ubuntu 终端检查缓存：

   ```bash
   redis-cli GET jotang:note:42
   redis-cli TTL jotang:note:42
   ```

   将示例 `42` 换成真实笔记 ID。首次 GET 后，TTL 应在 0–300 秒间；再次命中一般不会重置 TTL。

3. 使用有效 JWT 更新该笔记（PUT）；在成功响应后检查 `redis-cli EXISTS jotang:note:42` 应为 `0`，再 GET 应返回新内容并重建缓存。
4. 删除自己的笔记（DELETE）成功后，缓存键应不存在；再次 GET 应为 404。
5. Redis 停止或不可达时，GET 应继续从 MySQL 返回结果；恢复 Redis 后可以重新生成缓存。

**验收状态（2026-10-14）：** 原有 JWT 权限模拟测试 8/8 + 缓存模拟测试 8/8 全部通过。用户安装 Redis 服务端后，SSH 独立验证 Redis 6.0.16 的 `PONG`、仅本机监听 6379，以及 TestClient 连接**真实 Redis 服务端**的 13/13 项检查：缓存未命中→模拟 MySQL 回源→写入真实 Redis、300 秒 TTL、日期 JSON、缓存命中跳过 MySQL、PUT/DELETE 数据库模拟提交后删除真实缓存、404 不缓存。另使用真实 Redis Python 客户端连接不可达端口，验证 GET 可以回退模拟 MySQL。临时 Redis 键已删除，未修改用户实际笔记。**该组 HTTP 流程的 MySQL 部分使用模拟连接；真实数据库授权写操作（PUT/DELETE）联合验收仍待完成。** 随后用户亲自启动含 DB_PASSWORD 的 FastAPI 服务，SSH 从真实 HTTP 接口完成 **9/9 项 MySQL + Redis 读链路检查**：`GET /notes/1` 真实返回 200、对应真实 Redis 缓存 JSON 与 HTTP 响应一致、TTL 在 300 秒范围内、第二次 GET 不重置 TTL；请求未缓存的不存在 ID 返回 404，且不生成空值缓存（实际查询由真实 MySQL 执行）。整个真实联调未改动既有笔记数据。

## 官方思考题

- **缓存一致性：** 当前在 MySQL commit 后删除 Redis 缓存，同时设置 300 秒 TTL 作为兜底。Redis 删除失败、并发 GET 与 PUT 交错仍可能短暂返回旧值；当前实现是最终一致，不是严格一致。
- **缓存穿透：** 对不存在的 ID，可增加短 TTL 的空值缓存（例如 20 秒）或布隆过滤器。当前保留简单实现，未启用空值缓存。
- **缓存击穿：** 热门键过期时可引入互斥锁、提前刷新或不同过期时间；当前未实现，不能假定已解决。

后续 RabbitMQ 异步写入引入后，需要重新审视缓存删除的时机：应在数据库实际更新提交成功时，而不是请求刚入队时。
