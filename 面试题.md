# interview
针对个人简历准备的面试题以及答案
1️⃣ Go：Goroutine、Channel、GMP 调度模型
中级题

Goroutine 为什么比线程轻量？实现原理是啥？

Channel 为什么是线程安全的？底层结构是什么？

无缓冲 Channel 和带缓冲 Channel 的调度区别？

defer 为什么会有性能开销？

Go 的 map 为什么并发不安全？

GC 三色标记算法怎么工作？为什么不会 STW？

Goroutine 泄漏的场景有哪些？

高级题

GMP 模型中 M 和 P 的关系？为什么需要 work stealing？

Go 调度器如何避免全局锁？

阻塞系统调用对 GMP 的影响？如何优化？

Go Runtime 如何调度网络 IO？

Channel 底层锁竞争如何避免？为什么用了双锁 + ring buffer？

你如何在高并发场景下提高 Go 的吞吐？

sync.Pool 的重用原理是什么？什么时候不适合用？

Go 中的内存逃逸如何判断？怎么避免？

2️⃣ Gin / GoFrame 框架
核心中级题

Gin 是如何做到高性能路由匹配的？

中间件的执行顺序是怎么实现的？

GoFrame 的 IOC 容器是怎么做依赖注入的？

Gin 的 Context 是怎么做复用的？

为什么 Gin 不使用反射？带来了什么好处？

高级题

如何在 Gin / GoFrame 中实现一个可控制链路超时的 middleware？

高并发下如何减少 context.WithTimeout 的内存分配？

如何封装一个全局错误处理器（panic recover + 错误码 + trace）？

3️⃣ MySQL（索引、锁、分库分表、一致性）
中级题

聚簇索引和二级索引的区别是什么？为什么 MySQL 要用聚簇索引？

回表是什么？覆盖索引如何减少回表？

MySQL 的自增主键为什么会导致写热点？怎么优化？

MVCC 是如何实现快照读的？

MySQL 死锁常见场景有哪些？如何排查？

InnoDB 的行锁、间隙锁、临键锁分别是什么？

Count(*) 为什么会慢？

高级题

你怎么做分库分表？如何避免跨库查询？

分布式 ID 方案有哪些？雪花算法的缺点是什么？

如何实现 Redis + MySQL 的最终一致性？

MySQL 主从延迟有哪些解决方案？

如何设计一个可扩展的索引策略？

大表字段变更如何做到不停机？

4️ Redis（缓存、锁、计数、存储）
中级题

Redis 为什么快？（单线程、IO 多路复用、数据结构）

Redis 的过期策略和逐出策略有哪些？

Redis 集群 slot 分布是如何工作的？

Lua 脚本是怎么保证原子的？

高级题

分布式锁 RedLock 有哪些争议？生产环境怎么做更可靠？

如何实现一个 1 亿级访问量的分布式计数器？

大 key 问题如何排查？如何避免？

Redis 热 key 如何处理？

Redis 主从一致性如何保证？

5️ gRPC / Thrift / HTTP
中级题

gRPC 基于 HTTP/2 有哪些优势？

为什么 gRPC 的性能比 HTTP JSON 高？

Protobuf 的序列化结构？

gRPC 的连接池怎么管理？

gRPC 的 deadline / cancel 是怎么工作的？

高级题

如何在 gRPC 中实现灰度发布？

gRPC 长连接如何做负载均衡？

gRPC 调用链路如何做 tracing？

大型微服务的服务发现、熔断、限流怎么做？

你项目中的服务降级是怎么设计的？

6️⃣ Kafka / RocketMQ
中级题

Kafka 高吞吐的原因是什么？

ISR、HW、LEO 是什么？

为什么 Kafka 默认最多保证至少一次？

顺序消息如何实现？

消息堆积如何处理？

高级题

高并发下如何解决重复消费？

RocketMQ 的事务消息如何工作？

如何设计一个可回放的消息队列体系？

Kafka 分区过多会有什么问题？
7️⃣ Docker / K8s / CICD
中级题

Docker 镜像分层是怎么实现的？

为什么生产环境不建议 root 用户跑容器？

Kubernetes service 的流量转发机制？

Deployment 滚动更新流程？

K8s 如何处理 Pod crash？

高级题

你如何设计无损发布？

K8s 中如何实现自动扩容（HPA）？

Pod 网络模型（CNI）是如何通信的？

StatefulSet 为什么适合有状态服务？

如何排查集群中 CPU Throttle 问题？
8️⃣ Prometheus + Grafana
中级题

Prometheus 的 Pull 模型优势是什么？

Counter / Gauge / Histogram / Summary 区别？

什么是 P99？如何计算？

PromQL 如何写一个 QPS 查询？

如何监控 Goroutine、GC、Heap？

高级题

如何实现全链路 Trace？

如何构建一个 SLO + SLA 体系？

Grafana 如何与 Loki/Tempo 联合使用？

如何做报警的抖动防抖？
9️⃣ 网络：TCP、DNS、CDN
中级题

TCP 三次握手为什么不是两次？

TCP 粘包拆包怎么处理？

TIME_WAIT 多会导致什么？

DNS 缓存层级？

CDN 边缘节点的缓存策略？

高级题

如何排查线上丢包？（抓包 + 链路）

SYN Flood 防护方案？

CDN 回源慢如何诊断？

QUIC 相比 TCP 有哪些优势？
🔟 分布式理论与存储
中级题

CAP 理论是什么？

一致性协议：Paxos / Raft 有何不同？

分布式锁实现方式？

什么是雪崩、击穿、穿透？

高级题

如何设计一个分布式 KV？（如 Redis Lite）

如何实现分布式定时任务？

如何防止脑裂？

分布式事务 2PC / TCC 的优缺点？
