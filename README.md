## 技术面试知识库说明

这个仓库用于整理、沉淀后端技术面试相关的知识点和问答，方便在面试前快速复习和系统化查漏补缺，主要围绕 Go 后端技术栈展开。

### 目录结构

- `technologyInterview/`：面试知识库主目录
  - `golang.md`：Goroutine / Channel / GMP、GC、内存逃逸等 Go 语言核心原理
  - `golang性能优化.md`：Golang 性能优化专题（CPU / 内存 / GC / 并发调优）
  - `mysql.md`：MySQL 索引、锁、分库分表、一致性等常见面试题
  - `mysql-mvcc.md`：MySQL MVCC 相关专题
  - `redis.md`：Redis 性能、过期策略、缓存三大问题、主从一致性等
  - `mq.md`：Kafka / RocketMQ 的高吞吐、顺序消息、重复消费、事务消息等
  - `microservice-cloudnative.md`：Gin / GoFrame、gRPC、K8s、Prometheus / Grafana 等微服务与云原生相关题目
  - `linux-network.md`：TCP、DNS、CDN 等网络与 Linux 相关问题
  - `distributed-system.md`：CAP、Paxos / Raft、分布式锁、分布式事务等分布式系统专题
  - `k8s.md`：Kubernetes 相关补充笔记
  - `cdn系统总结.md`：CDN / 边缘加速体系总结
  - `java值传递.md`：Java 值传递机制
  - `DD.md`：草稿 / 临时记录
  - `面试题.md`：综合版大纲（所有专题的总索引）

- `program/`：与面试相关的小程序 / 示例代码或其他资料

### 推荐使用方式

- **面试前冲刺**  
  从 `technologyInterview/面试题.md` 里的目录开始自上而下快速过一遍，对照对应专题文件查缺补漏。

- **系统化复习**  
  按模块单独攻克，例如：
  - 想重点准备 Go：看 `golang.md` + `golang性能优化.md`
  - 想补数据库：看 `mysql.md` + `mysql-mvcc.md`
  - 想准备分布式 / 高并发：看 `redis.md`、`mq.md`、`distributed-system.md` 等。

- **持续维护**  
  每次刷题、踩坑、看文章或做项目时，把新的思考和案例追加到对应文件中，让这个仓库成为你的「个人知识库 + 面试手册」。

