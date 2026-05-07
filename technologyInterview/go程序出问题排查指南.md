# Go 线上服务 CPU / 内存异常排查手册

> 场景：无 Prometheus/Grafana、无 pprof、无 trace 时的应急排查路径。

## 目录

- [一、问题背景](#一问题背景)
- [二、核心排查思路](#二核心排查思路)
- [三、第一步：保留现场](#三第一步保留现场)
- [四、第二步：找到异常 Go 进程](#四第二步找到异常-go-进程)
- [五、第三步：查看线程级 CPU](#五第三步查看线程级-cpu)
- [六、第四步：线程 ID 转十六进制](#六第四步线程-id-转十六进制)
- [七、第五步：Go 程序打印 goroutine 堆栈](#七第五步go-程序打印-goroutine-堆栈)
- [八、查看 goroutine 日志](#八查看-goroutine-日志)
- [九、通过线程定位具体代码](#九通过线程定位具体代码)
- [十、CPU 飙升常见原因](#十cpu-飙升常见原因)
- [十一、内存暴涨排查](#十一内存暴涨排查)
- [十二、内存暴涨常见原因](#十二内存暴涨常见原因)
- [十三、通过 goroutine 状态判断问题](#十三通过-goroutine-状态判断问题)
- [十四、排查网络连接](#十四排查网络连接)
- [十五、排查 IO 问题](#十五排查-io-问题)
- [十六、Kubernetes 环境排查](#十六kubernetes-环境排查)
- [十七、线上止血方案](#十七线上止血方案)
- [十八、推荐线上必备能力](#十八推荐线上必备能力)

---

## 一、问题背景

线上 Go 服务突然出现：

- CPU 飙升
- 内存暴涨
- QPS 下降
- 接口超时
- Pod 重启
- 服务不可用

但此时：

- 没有监控
- 没有 Prometheus/Grafana
- 没有 pprof
- 没有 trace

**问题：如何快速定位问题？**

---

## 二、核心排查思路

### 核心原则

**先保现场，再定位问题** —— 不要一上来直接重启。

### 正确流程

1. 保现场  
2. 看系统资源  
3. 定位异常进程  
4. 定位异常线程  
5. 打印 Go 堆栈  
6. 分析 goroutine  
7. 结合日志确认根因  
8. 止血恢复  

---

## 三、第一步：保留现场

先把系统现场保存下来。

### 1. 保存系统信息

```bash
date
hostname
uptime
free -h
df -h
```

### 2. 保存 top 信息

```bash
top -b -n 1 > top.log
```

### 3. 查看 CPU 最高进程

```bash
ps aux --sort=-%cpu | head -30 > ps_cpu.log
```

### 4. 查看内存最高进程

```bash
ps aux --sort=-%mem | head -30 > ps_mem.log
```

---

## 四、第二步：找到异常 Go 进程

查找程序 PID：

```bash
ps aux | grep 程序名
```

示例输出：

```text
app      12345  300  40 ...
```

说明：**PID = 12345**（示例）。

---

## 五、第三步：查看线程级 CPU

### 查看 Go 进程内部线程

```bash
top -Hp 12345
```

**作用：** 查看 Go 程序内部哪个线程 CPU 高。

示例：

| PID   | USER | %CPU |
|-------|------|------|
| 12388 | app  | 99.5 |

说明：**线程 12388 正在疯狂消耗 CPU**。

---

## 六、第四步：线程 ID 转十六进制

Go dump 堆栈时使用的是**十六进制线程 ID**。

转换：

```bash
printf "%x\n" 12388
```

输出示例：`3064`

对应关系：

| 十进制线程 ID | 十六进制 |
|---------------|----------|
| 12388         | `0x3064` |

---

## 七、第五步：Go 程序打印 goroutine 堆栈

即使没有 pprof，也能打印堆栈。

### 方法一（推荐）

```bash
kill -QUIT 12345
```

或：

```bash
kill -3 12345
```

**注意：**

- **不会杀死进程**
- 只是通知 Go Runtime：**打印所有 goroutine 堆栈**

---

## 八、查看 goroutine 日志

### systemd 服务

```bash
journalctl -u 服务名 -n 500
```

### nohup 启动

```bash
tail -500 nohup.out
```

### Kubernetes

```bash
kubectl logs pod名 --tail=500
```

---

## 九、通过线程定位具体代码

搜索刚才的十六进制线程 ID：

```bash
grep -n "3064" goroutine.log
```

即可找到：

- 哪个 goroutine 正在占用 CPU
- 具体执行的函数（栈信息）

示例栈帧：

```text
project/service.(*Worker).Run()
```

---

## 十、CPU 飙升常见原因

### 1. 死循环

典型代码：

```go
for {
}
```

或：

```go
for {
    select {
    default:
    }
}
```

**特点：** 线程 CPU 接近 100%。

### 2. goroutine 泄漏

查看 goroutine 数量：

```bash
grep -c "goroutine" goroutine.log
```

若达到**几万 / 几十万**，基本可判断为 goroutine 泄漏。

### 3. GC 压力过大

**表现：** CPU 高、系统抖动、延迟高。

**常见原因：**

- 大量对象创建
- slice/map 无限增长
- 大对象频繁分配

### 4. 无限重试

```go
for {
    err := call()
    if err != nil {
        continue
    }
}
```

**后果：** CPU 飙升、请求风暴。

### 5. 日志疯狂打印

```go
for {
    log.Println("error")
}
```

**后果：** CPU + IO 双高。

---

## 十一、内存暴涨排查

### 查看 Go 进程内存

```bash
cat /proc/12345/status | egrep "VmRSS|VmSize|VmData|Threads"
```

| 字段    | 含义           |
|---------|----------------|
| VmRSS   | 实际物理内存   |
| VmSize  | 虚拟内存       |
| VmData  | 堆内存         |
| Threads | 线程数         |

### 查看内存映射

```bash
pmap -x 12345 | tail -20
```

---

## 十二、内存暴涨常见原因

### 1. map/slice 无限增长

例如：

```go
cache[key] = value
```

没有淘汰机制。

### 2. goroutine 泄漏

大量 goroutine：每个 goroutine 默认约 **2KB** 栈空间；几十万 goroutine 时内存占用会非常大。

### 3. 队列堆积

例如 `chan task`：**生产速度 > 消费速度**。

### 4. 下游阻塞

例如：

- MySQL 慢
- Redis 卡
- HTTP 下游超时

**后果：** 请求不断堆积。

### 5. 大对象未释放

例如：`[]byte`、大 JSON、图片、文件等仍被引用。

---

## 十三、通过 goroutine 状态判断问题

查看 goroutine **卡在哪里**，常见状态与含义：

| 状态              | 含义说明                 |
|-------------------|--------------------------|
| chan send         | 生产者过快 / 消费者太慢  |
| chan receive      | 消费者阻塞 / 没人生产    |
| sync.Mutex.Lock   | 锁竞争严重               |
| database/sql      | 数据库连接池耗尽         |
| net/http          | 下游 HTTP 请求阻塞       |

---

## 十四、排查网络连接

### 查看连接数

```bash
ss -antp | grep 12345 | wc -l
```

### 查看连接状态

```bash
ss -antp | grep 12345
```

| 状态       | 含义           |
|------------|----------------|
| ESTAB      | 正常连接       |
| CLOSE-WAIT | 连接未关闭     |
| TIME-WAIT  | 短连接过多     |
| SYN-SENT   | 下游不可达     |

**CLOSE-WAIT 很多** 时，常见原因是未调用 `resp.Body.Close()`。

正确写法：

```go
defer resp.Body.Close()
```

---

## 十五、排查 IO 问题

### 查看系统 IO

```bash
iostat -x 1
```

### 查看系统状态

```bash
vmstat 1
```

| 字段 | 含义         |
|------|--------------|
| us   | 用户态 CPU   |
| sy   | 内核态 CPU   |
| wa   | IO 等待      |
| si/so| swap         |
| r    | 运行队列     |

**wa 高** 说明磁盘 IO 卡住，**不一定是 CPU 问题**。

---

## 十六、Kubernetes 环境排查

### 查看 Pod 资源

```bash
kubectl top pod -n namespace
```

### 查看 Pod 状态

```bash
kubectl describe pod pod名 -n namespace
```

### 查看日志

```bash
kubectl logs pod名 -n namespace --tail=500
```

### 进入容器

```bash
kubectl exec -it pod名 -n namespace -- sh
```

容器内查看线程：

```bash
top -H
```

---

## 十七、线上止血方案

若已影响业务，可按优先级选用：

### 1. 摘流量

从 LB 或网关摘除异常实例。

### 2. 扩容

快速增加 Pod：

```bash
kubectl scale deploy app --replicas=10
```

### 3. 限流

例如：网关限流、接口限流、MQ 限流。

### 4. 降级

关闭非核心能力，例如：推荐、搜索、统计等。

### 5. 回滚版本

若为新版本导致：**立即回滚**。

---

## 十八、推荐线上必备能力

建议线上服务默认具备：

### 1. pprof

```go
import _ "net/http/pprof"
```

### 2. Prometheus

监控建议覆盖：CPU、内存、goroutine、GC、QPS、P99 等。

### 3. 日志采集

推荐：ELK、Loki 等。

### 4. trace

推荐：Jaeger、SkyWalking 等。

---

**文档说明：** 文中 `12345`、`12388`、`3064` 等为示例，请替换为实际 PID / 线程 ID / 十六进制值。
