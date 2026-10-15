#!/usr/bin/env python3
"""用真实 HTTP 接口复测后端招新主线，默认只创建并清理一条临时笔记。

使用现有账户登录；密码通过 getpass 输入，不能放到命令行、Git 或截图中。
支持同步（201/200）与异步（202 + 任务轮询）两种写入模式。
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import redis


class CheckFailure(Exception):
    pass


def api(base: str, method: str, path: str, body=None, token: str | None = None):
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(
        base + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=15) as response:
            status, raw = response.status, response.read()
    except HTTPError as exc:
        status, raw = exc.code, exc.read()
    except (URLError, TimeoutError) as exc:
        raise CheckFailure(f"无法连接 API：{exc}") from exc
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {"detail": "返回非 JSON"}
    return status, data


def expect(actual: bool, message: str):
    if not actual:
        raise CheckFailure(message)
    print("[PASS]", message)


def wait_task(base: str, task_id: str, token: str):
    for _ in range(40):
        status, data = api(base, "GET", "/tasks/" + task_id, token=token)
        if status != 200:
            raise CheckFailure(f"查询任务失败，HTTP {status}")
        if data.get("status") == "completed":
            return data.get("result") or {}
        if data.get("status") == "failed":
            raise CheckFailure(f"Worker 执行失败：{data.get('error', '未知原因')}")
        time.sleep(0.5)
    raise CheckFailure("任务 20 秒内未完成，请检查 Worker / RabbitMQ")


def write_note(base: str, method: str, path: str, body, token: str):
    status, data = api(base, method, path, body, token)
    if status == 202:
        task_id = data.get("task_id")
        if not task_id:
            raise CheckFailure("HTTP 202 缺少 task_id")
        result = wait_task(base, task_id, token)
        print("      HTTP 202 → RabbitMQ → Worker completed")
        return result
    if status not in (200, 201):
        raise CheckFailure(f"{method} {path} 返回 HTTP {status}：{data.get('detail', '请检查日志')}")
    print(f"      同步 HTTP {status}")
    return data


def main():
    parser = argparse.ArgumentParser(description="JotangNote 真实接口收尾验收（不输出口令/JWT）")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--username", help="已有测试账号用户名；未指定时交互输入")
    parser.add_argument("--keep-note", action="store_true", help="保留本轮测试笔记供网页/AI 截图，需自行删除")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    username = args.username or input("测试用户名：").strip()
    if not username:
        raise CheckFailure("用户名不能为空")
    password = getpass.getpass("密码（不显示）：")
    if not password:
        raise CheckFailure("密码不能为空")

    status, login = api(base, "POST", "/login", {"username": username, "password": password})
    expect(status == 200 and bool(login.get("access_token")), "真实账号密码登录 200")
    token = login["access_token"]
    del password, login

    status, _ = api(base, "POST", "/notes", {"title": "unauthorized", "content": "unauthorized"})
    expect(status == 401, "无 JWT 创建笔记被拒绝（401）")

    cache = redis.Redis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
    try:
        cache.ping()
    except redis.RedisError as exc:
        raise CheckFailure(f"Redis 不可用：{exc}") from exc

    test_title = "招新验收临时笔记 " + datetime.now().strftime("%m%d-%H%M%S")
    note_id = None
    deleted = False
    try:
        created = write_note(base, "POST", "/notes",
                             {"title": test_title, "content": "这是只用于测试的无隐私笔记。"}, token)
        note_id = created.get("id")
        expect(isinstance(note_id, int) and note_id > 0, "新增笔记返回有效 ID")

        key = f"jotang:note:{note_id}"
        status, result = api(base, "GET", f"/notes/{note_id}")
        expect(status == 200 and result.get("title") == test_title, "真实 MySQL GET 回读")
        ttl = cache.ttl(key)
        expect(0 < ttl <= 300, "首次 GET 已写入 Redis 缓存（TTL 1～300 秒）")
        status, result = api(base, "GET", f"/notes/{note_id}")
        expect(status == 200 and result.get("title") == test_title, "第二次 GET 正确返回缓存内容")
        expect(0 < cache.ttl(key) <= ttl, "缓存命中没有重置 TTL")

        updated = "异步/同步修改后内容，验证缓存失效。"
        write_note(base, "PUT", f"/notes/{note_id}",
                   {"title": test_title + " 已修改", "content": updated}, token)
        expect(not cache.exists(key), "PUT 完成后 Redis 已删除旧缓存")
        status, result = api(base, "GET", f"/notes/{note_id}")
        expect(status == 200 and result.get("content") == updated, "PUT 后真实 MySQL 返回新内容")

        if args.keep_note:
            print(f"[KEEP] 测试笔记 ID={note_id}；用于网页、AI Tool Use 截图，完成后请自行删除。")
        else:
            write_note(base, "DELETE", f"/notes/{note_id}", None, token)
            deleted = True
            expect(not cache.exists(key), "DELETE 完成后 Redis 缓存不存在")
            status, _ = api(base, "GET", f"/notes/{note_id}")
            expect(status == 404, "DELETE 后再次 GET 返回 404")
            print("[DONE] 已删除本轮临时笔记；未修改其他笔记。")

    finally:
        if note_id and not deleted and not args.keep_note:
            try:
                write_note(base, "DELETE", f"/notes/{note_id}", None, token)
                print("[CLEANUP] 已尝试清理本轮临时笔记。")
            except Exception as exc:
                print(f"[CLEANUP WARNING] 测试笔记 ID={note_id} 未能自动清理：{exc}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (CheckFailure, KeyboardInterrupt) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        sys.exit(1)
