# Part 2 后端常用技术栈 — RabbitMQ

> 学习状态（截至 2026-10-09）：已在 Ubuntu Docker 中运行 RabbitMQ，并通过 Pika 做最小发送/接收练习。发送入队有独立核验，消费者运行及 ACK 输出由用户反馈成功；**代码逐行理解与底层实现尚未掌握，需下次继续。**

## 1. RabbitMQ 是什么？为什么需要 MQ？

MQ（Message Queue，消息队列）用于在程序之间传递消息。RabbitMQ 是消息代理（Message Broker）：生产者把任务信息作为消息发布，消费者可以稍后取得消息并处理。

在 JotangNote 中，用户提交“生成笔记摘要”后，FastAPI 不一定需要等待 AI 把摘要算完。可以先把任务放入队列，由后台 Worker 处理，接口先返回“已接受/等待处理”，而不是直接返回“摘要生成成功”。**消息成功入队 ≠ 业务已经执行成功**。异步接口可以使用 HTTP 202 Accepted，并让用户通过任务状态确认最终结果。

引入 MQ 的常见原因：

1. **异步处理**：耗时任务交给后台执行，缩短 HTTP 请求等待时间。
2. **削峰填谷**：高峰时先让任务排队，低峰时继续消费，避免所有任务瞬间压到下游。若长期生产速度大于消费速度，队列仍会积压；可以增加 Worker，也可用限流、背压控制流量。
3. **服务解耦**：笔记服务发布“笔记已创建”事件，通知服务、搜索服务分别消费自己需要的消息，不必让笔记服务直接调用所有下游服务。

## 2. 一条消息经过哪些角色？

基本流程：**Producer（生产者） → Exchange（交换机） → Queue（队列） → Consumer（消费者/Worker）**。

- Producer：例如 FastAPI，把待处理任务编码成消息并发布。
- Exchange：根据路由规则把消息送往合适的队列；默认交换机写为 `exchange=""`。
- Queue：保存等待消费的消息。没有 Worker 时，满足队列和消息的可靠性条件才能保证消息在故障后仍保留。
- Consumer：例如后台 Python Worker，接收消息并执行数据库操作、生成摘要等任务。

简单使用默认交换机时，`routing_key="tasks"` 表示路由到名为 `tasks` 的队列；它必须存在，否则在默认发布设置下，无法路由的消息可能被丢弃。实际系统还要考虑消息是否成功到达 Broker 的确认机制。

**顺序注意**：队列可以按入队顺序安排消息，但多个 Worker 并行、重试等情况下，消息不保证按原顺序处理完成。涉及同一篇笔记的先后修改，后续需要专门考虑顺序性。

## 3. ACK：收到消息不等于执行成功

消费者使用 `auto_ack=False` 时，处理成功后再执行：

```python
ch.basic_ack(delivery_tag=method.delivery_tag)
```

- `ch` 是本次消费使用的 Channel；`method.delivery_tag` 是该 Channel 内本次消息投递的编号，并不是业务任务 ID。
- ACK 表示**这次消息投递已处理完毕**。即使发现任务之前已经做过，这次投递仍需要确认。
- 如果 Worker 在 ACK 前崩溃，RabbitMQ 检测到连接/通道关闭后，可以重新投递未确认的消息。
- 如果数据库操作还未成功就提前 ACK，后续失败时 RabbitMQ 已认为消息处理完，可能导致业务任务丢失。
- 如果 Worker 没崩溃但业务失败，也不能只想着“不 ACK 就一定立即重试”；还需要设计异常处理、`basic_nack()`、重试或死信等策略。

## 4. 重复消费与幂等性

例如 Worker 已在 MySQL 中新增一篇笔记，却在 ACK 前崩溃。RabbitMQ 重投这条消息时，如果直接再执行插入，可能出现两篇相同的笔记。

**幂等性**：同一业务操作执行多次和执行一次，最终效果保持一致。

一种处理思路：为每个业务任务设唯一 `task_id`，Worker 检查是否处理过；已完成的不重复写 MySQL，而是直接确认本次投递。实际代码不能只靠“先查询再插入”来避免并发重复，还应考虑数据库唯一约束和事务等手段。

## 5. Python 如何发送、接收消息？（示例与最小实践）

Python 可以使用 `pika` 与 RabbitMQ 通信。先理解了以下接口和语法：

| 接口 / 语法 | 作用 |
| --- | --- |
| `pika.BlockingConnection(parameters)` | 建立 RabbitMQ 连接 |
| `with ... as connection` | 用上下文管理器在离开代码块时清理连接 |
| `connection.channel()` | 创建通道 |
| `channel.queue_declare(queue="hello")` | 声明队列，不存在时创建 |
| `channel.basic_publish(...)` | 将消息发布到交换机，由它路由至队列 |
| `channel.basic_consume(...)` | 注册队列和收到消息时调用的回调函数 |
| `channel.start_consuming()` | 进入持续处理消息的循环 |
| `body.decode("utf-8")` | 将收到的 bytes 转成字符串 |

### 发送方的核心片段

```python
channel.queue_declare(queue="hello")
channel.basic_publish(
    exchange="",
    routing_key="hello",
    body="Hello RabbitMQ!"
)
```

### 接收方的核心片段

```python
def callback(ch, method, properties, body):
    print(body.decode("utf-8"))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(
    queue="hello",
    on_message_callback=callback,
    auto_ack=False
)
channel.start_consuming()
```

`callback` 是函数本身（不加括号），由 Pika 收到消息后调用。`basic_consume()` 是注册消费规则；`start_consuming()` 才开始持续处理消息。以上代码先用于讲解结构；2026-10-09 已在 Project/src/send.py 和 Project/src/receive.py 做最小实测。生产环境仍需考虑连接异常、消息/队列持久化、发布确认、重试和权限认证。

## 6. 概念问答与能力边界

2026-10-08 的问答中，已能解释：为什么入队后只能说“提交成功”；一个 Worker 如何排队处理任务；增加 Worker 与限流/背压的取舍；下游通知服务宕机时其他服务为何可以继续；ACK 为什么不能早于数据库写入；消息重复后为什么要做幂等处理。

另外补学 Python 的 `with`、函数作为参数与回调、`bytes`/`str`、`decode()`。已读懂 Producer/Consumer 示例的主要执行顺序，但**还不能把阅读示例等同于独立编写和运行成功**。

## 7. 2026-10-09 最小实测

- **环境：** Ubuntu 22.04 VM，Docker 29.1.3，RabbitMQ Docker 镜像 rabbitmq:4-management，绑定到 Ubuntu 本机 127.0.0.1:5672 (AMQP) 与 127.0.0.1:15672 (Web 管理端口)，两端口监听且管理页 HTTP 200 经 SSH 核验。
- **下载故障：** Docker Hub 一度 DNS 解析错误；网络检查发现 NAT 上游 DNS 192.168.43.2 与 Fake-IP 地址。网络恢复后重新拉取镜像成功。
- **Python 客户端：** 虚拟环境已装 pika 1.4.4；生产者 Project/src/send.py 和消费者 Project/src/receive.py 均通过语法检查，认证密码通过环境变量 RABBITMQ_PASSWORD 读取，不在源码中保存。
- **兼容性：** 当下 RabbitMQ 镜像中 queue_declare(queue="hello") 因 transient_nonexcl_queues 特性触发 541；改为 queue_declare(queue="hello", durable=True) 后继续。队列持久化不等于消息持久化。
- **发送证据：** 生产者运行后，助手通过 AMQP 被动查询发现 hello 队列存在，messages_ready=1、consumers=0，证明已有消息入队。
- **消费证据与边界：** 用户确认消费者程序运行完成，代码中使用 auto_ack=False，回调接收、打印消息后执行 basic_ack。助手核对源码但未取得用户当时的终端输出、也未独立复查消费后的队列计数；因此仅按用户反馈记录本轮消费结果。
- **暂未验证：** ACK 前崩溃后的重投、幂等性、消息发布确认、消息持久化、完整截图和异常重试。

**下次继续：** 先结合已存在的两个脚本补 Python 基础语法（with、回调、字节/字符串、环境变量）与 Pika API、RabbitMQ 底层消息投递机制，不重复安装。之后继续启蒙篇 AI Agent、HTTP / API / JSON / HTTPS；补截图与正式提交收尾视实际要求处理。

## AI 使用说明

本文由 ChatGPT 根据 2026-10-08 问答、2026-10-09 用户实际练习和 SSH 核验整理，区分用户反馈与独立核验；不把尚未验证的底层可靠性或代码掌握程度写成已完成。
