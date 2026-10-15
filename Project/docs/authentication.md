# 用户登录认证与笔记作者权限

## 功能流程

1. `POST /register`：注册用户，使用 Argon2 保存密码哈希。
2. `POST /login`：按用户名查询并验证密码；成功返回 `access_token`、`token_type=bearer`，以及 `expires_in=7200` 秒（2 小时）。
3. 后续调用 `POST /notes`、`PUT /notes/{note_id}`、`DELETE /notes/{note_id}`，需要携带请求头 `Authorization: Bearer <token>`。
4. `get_current_user` 通过 `Depends` 取得 Token，校验 JWT 签名、`exp` 过期时间和 `sub` 用户 ID，并查询该用户是否仍存在。
5. 新增笔记时作者从当前用户取得，不再由请求 JSON 指定；修改、删除笔记时核对作者，拒绝非作者操作（403）。
6. `GET /notes/{note_id}` 仍可公开查询。

## 核心思路

- JWT 是**签名令牌**，而不是加密文本，载荷中只保存用户 ID（`sub`）和过期时间（`exp`），不包含密码。
- 服务器用 `JWT_SECRET_KEY` 验证签名，无需每次重新输入密码；过期后重新登录。
- `HTTPBearer` 负责读取请求头，`Depends` 复用认证逻辑。
- Token 使用 HS256 签名，有效期为 120 分钟。
- `notes.author` 保存作者用户名；修改、删除时与当前登录用户的用户名比较，不能相信客户端自行填写的作者身份。
- 当前没有实现刷新 Token 或主动撤销 Token。

## 环境和启动

项目使用 Python 3.13 虚拟环境。在仓库根目录安装依赖：

```bash
.venv/bin/python --version  # 应为 3.13.x
.venv/bin/python -m pip install -r requirements.txt
```

在项目根目录的 `.env` 配置 `JWT_SECRET_KEY`。可通过 `openssl rand -hex 32` 生成随机密钥；`.env` 已被 Git 忽略，不应上传。

在启动服务的终端输入数据库密码：

```bash
read -rsp "DB_PASSWORD: " DB_PASSWORD
echo
export DB_PASSWORD
.venv/bin/uvicorn app:app --app-dir Project/src --host 0.0.0.0 --port 8080 --reload
```

## Swagger 复测步骤

打开 `http://<Ubuntu虚拟机IP>:8080/docs`：

1. 调用 `POST /login`，正确密码应返回 200 和 Token，错误密码返回 401。
2. 点击右上角 **Authorize**，填入返回的 Token（无需手动添加 `Bearer `）。
3. 调用 `POST /notes` 创建笔记，验证作者自动为当前用户。
4. 使用另一个已注册账号的 Token，尝试修改/删除第一位用户的笔记，应为 403。
5. 用原作者的 Token 修改/删除，应该成功。
6. 不带 Token 或携带过期 Token 的写请求应返回 401。

## 网页操作截图（2026-10-15）

通过网页注册并登录测试账号，创建笔记后根据 ID 查询、修改和删除。写操作经 RabbitMQ Worker 异步完成；截图记录了登录、创建、查询和修改的结果。

![测试账号已登录工作台](assets/jotang-logged-in.png)

![网页新增笔记成功](assets/jotang-note-create.png)

![网页读取真实 MySQL 笔记](assets/jotang-note-read.png)

![网页提交异步修改成功](assets/jotang-note-update.png)

测试笔记已删除，之后再次查询返回 404。

## 测试

自动化测试在 `Project/tests/test_auth.py`，可用：

```bash
.venv/bin/python -m unittest discover -s Project/tests -v
```

`test_auth.py` 包含 8 项测试，覆盖登录、JWT 校验和作者权限，其中数据库使用模拟对象；网页 CRUD 另使用真实数据库验证。跨账号修改/删除返回 403 由自动化测试覆盖。
