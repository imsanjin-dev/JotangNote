# Part 2 后端常用技术栈 — RabbitMQ

## 1. RabbitMQ 是什么？为什么需要消息队列？

RabbitMQ 是一种消息代理（Message Broker），用于接收、路由和投递程序之间的消息。消息队列（Message Queue，MQ）可以让发送任务的程序和执行任务的程序不必同步等待。

例如在 JotangNote 中，用户发起“生成笔记摘要”后，FastAPI 可以先把任务交给 RabbitMQ，由后台 Worker 调用 AI 处理。接口可以先返回“任务已接受”，用户再通过任务状态查看最终结果。**消息成功入队不等于摘要已经生成成功。**

使用 MQ 的主要原因：

- **异步处理**：耗时工作交给后台执行，缩短接口等待时间；
- **削峰填谷**：高峰期让任务排队，避免下游服务瞬间承受过多请求；
- **服务解耦**：发送方发布消息后，不需要直接调用所有处理方。

如果消息产生速度长期高于消费速度，队列仍然会积压，需要增加 Worker、限制请求量或采取其他措施。

## 2. 消息是怎样传递的？

基本流程：

```text
Producer（生产者）
       ↓
Exchange（交换机）
       ↓
Queue（队列）
       ↓
Consumer（消费者 / Worker）
```

- **Producer**：发布消息，例如 FastAPI 提交摘要任务；
- **Exchange**：根据路由规则将消息送到相应队列；
- **Queue**：保存等待投递的消息；
- **Consumer**：订阅队列，收到消息后执行业务。

默认交换机的写法是 `exchange=""`。使用默认交换机时，`routing_key="hello"` 表示将消息路由到名为 `hello` 的队列（前提是队列存在）。

同一队列可以有多个 Worker 分担消息处理。队列通常按顺序安排投递，但多个 Worker 并发、失败重试时，任务完成的顺序不一定与入队顺序一致。

## 3. Connection 与 Channel

Python 可以通过 Pika 使用 AMQP 0-9-1 协议与 RabbitMQ 通信。Pika 将发布、消费等操作编码为协议帧，再通过 TCP 连接发送到 RabbitMQ；RabbitMQ 负责解析、路由和投递消息。

- **Connection**：与 RabbitMQ 建立的网络连接；
- **Channel**：连接上的逻辑通信通道，多个 Channel 可以复用一条 TCP 连接。

`pika.BlockingConnection(parameters)` 建立连接，`connection.channel()` 创建 Channel。`with ... as connection` 用于在离开代码块时关闭连接。

使用 Pika 的方法并不是直接修改 RabbitMQ 内部的数据结构，而是向 Broker 发送协议操作。

## 4. 如何使用 Python 发送和接收消息？

Pika 中常见的 API：

| API | 作用 |
| --- | --- |
| `PlainCredentials(...)` | 提供连接用户名和密码 |
| `ConnectionParameters(...)` | 配置主机、端口和认证信息 |
| `BlockingConnection(...)` | 建立连接 |
| `connection.channel()` | 创建 Channel |
| `queue_declare(...)` | 声明队列，不存在时创建 |
| `basic_publish(...)` | 发布消息 |
| `basic_consume(...)` | 注册消费者回调 |
| `start_consuming()` | 持续接收并处理消息 |
| `basic_ack(...)` | 确认某次消息投递完成 |

### 发送消息

```python
channel.queue_declare(queue="hello", durable=True)
channel.basic_publish(
    exchange="",
    routing_key="hello",
    body="Hello RabbitMQ!"
)
```

`queue_declare` 确保队列存在，`basic_publish` 把消息发布到交换机，再由交换机路由。`durable=True` 表示声明持久化队列，**不代表消息本身就一定持久化**。

### 接收消息

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

`basic_consume()` 负责注册回调函数，`start_consuming()` 才会进入消费循环。`callback` 作为函数对象传入，不是在注册时立即执行。

收到的 `body` 是 `bytes`，使用 `decode("utf-8")` 转为字符串。`auto_ack=False` 表示不自动确认，而由代码在处理完成后执行 ACK。

实际练习代码见 `Project/src/send.py` 和 `Project/src/receive.py`。连接密码通过环境变量 `RABBITMQ_PASSWORD` 读取，避免直接写在源码中。

## 5. ACK、消息可靠性和幂等性

**消费者收到消息，不代表业务执行成功。** 手动确认的基本原则是先完成业务处理，再发送 ACK：

```python
ch.basic_ack(delivery_tag=method.delivery_tag)
```

这里的 `delivery_tag` 标记的是当前 Channel 上的一次消息投递，并不是笔记 ID 或业务任务 ID。

如果 Worker 在写入数据库之前就发送 ACK，随后程序出错，消息可能已经被 RabbitMQ 视为处理完成。反过来，如果数据库写入成功但 Worker 在 ACK 前崩溃，连接关闭后未确认的消息可能被重新投递。

这就引出了**幂等性**：同一业务操作执行多次，最终结果应与执行一次一致。

例如创建笔记任务被重复投递时，不能每次都新增一篇相同的笔记。可以给任务设置唯一 `task_id`，并结合数据库唯一约束、事务等机制避免重复写入；单纯“先查询再插入”仍可能存在并发竞争问题。

实际系统还需要区分：

- **手动 ACK**：确认消费者成功处理了这次投递；
- **持久化**：队列持久化和消息持久化是不同设置；
- **发布确认**：发送方需要确认 Broker 是否接收消息；
- **失败处理**：业务出错时设计拒绝、重试或死信队列等策略。

RabbitMQ 并不自动保证业务只执行一次。可靠处理还依赖应用自身的设计。

## 6. 本阶段理解与实践情况

已理解 RabbitMQ 异步处理、削峰和解耦的作用，以及生产者、交换机、队列、消费者、ACK、重复投递和幂等性的基本关系。

已在 Ubuntu 虚拟机中使用 Docker 启动 RabbitMQ，并通过 Python Pika 编写 `send.py`、`receive.py` 进行最小收发练习。发送入队经过独立检查；消费运行由实际操作反馈确认，当时没有额外核验消费后的队列计数和完整 ACK 日志。

目前能理解示例代码的用途和整体流程，但脱离示例独立组织代码、AMQP 的底层细节、故障重投和持久化等可靠性场景仍有待通过实践掌握。后续在 JotangNote 入门篇的真实异步任务中继续学习，不单独重复收发示例。

## AI 使用说明

使用 ChatGPT 辅助解释 RabbitMQ 的原理、Pika API、ACK 与幂等性，并整理笔记；已实际练习的收发操作与尚未验证的可靠性场景在上文分开说明。
