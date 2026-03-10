- [Golang 面试题](#golang-面试题)
- [1 Goroutine 为什么比线程轻量？实现原理是啥？](#1-goroutine-为什么比线程轻量实现原理是啥)
- [2 GMP 调度模型](#2-gmp-调度模型)
  - [2.1 gmp模型](#21-gmp模型)
  - [2.2 调度流程](#22-调度流程)
  - [2.3 goroutine发生系统调用阻塞有什么影响？](#23-goroutine发生系统调用阻塞有什么影响)
  - [2.4 如何优化？](#24-如何优化)
    - [2.4.1 Go Runtime 如何解决这个问题？](#241-go-runtime-如何解决这个问题)
    - [2.4.2 网络 IO 的进一步优化（netpoll）](#242-网络-io-的进一步优化netpoll)
    - [2.4.3 调度层面的优化](#243-调度层面的优化)
  - [2.5 如果大量 goroutine 都在 syscall，会发生什么？](#25-如果大量-goroutine-都在-syscall会发生什么)
  - [2.6 为什么需要P](#26-为什么需要p)
  - [2.7 GMP 模型中 M 和 P 的关系？为什么需要 work stealing？](#27-gmp-模型中-m-和-p-的关系为什么需要-work-stealing)
  - [2.8 为什么 Go 的 runqueue 长度是 256？](#28-为什么-go-的-runqueue-长度是-256)
- [3 Channel](#3-channel)
  - [3.1 为什么 Channel 是线程安全的？](#31-为什么-channel-是线程安全的)
  - [3.2 Channel 的底层结构](#32-channel-的底层结构)
  - [3.3 Channel 的核心结构](#33-channel-的核心结构)
  - [3.4 发送数据时发生了什么](#34-发送数据时发生了什么)
    - [3.4.1 有等待的接收者](#341-有等待的接收者)
    - [3.4.2 buffer 有空间](#342-buffer-有空间)
    - [3.4.3 buffer 满了](#343-buffer-满了)
    - [3.4.4 Channel send 的三步判断 总结](#344-channel-send-的三步判断-总结)
  - [3.5 无缓冲 Channel 和带缓冲 Channel 的调度区别？](#35-无缓冲-channel-和带缓冲-channel-的调度区别)
    - [3.5.1 无缓冲调度流程图](#351-无缓冲调度流程图)
    - [3.5.2 有缓冲channel调度流程](#352-有缓冲channel调度流程)
    - [3.5.3核心调度区别](#353核心调度区别)
  - [3.6 Channel 底层锁竞争如何避免？为什么用了双锁 + ring buffer？](#36-channel-底层锁竞争如何避免为什么用了双锁--ring-buffer)
- [4 Map](#4-map)
  - [4.1 map为什么不是线程安全的](#41-map为什么不是线程安全的)
- [5 GC](#5-gc)
  - [5.1 GC算法是什么](#51-gc算法是什么)
  - [5.2 为什么不会 STW？](#52-为什么不会-stw)
- [6 Goroutine 泄漏的场景有哪些？](#6-goroutine-泄漏的场景有哪些)
  - [6.1 Channel 读阻塞（没有生产者）](#61-channel-读阻塞没有生产者)
  - [6.2 Channel 写阻塞（没有消费者）](#62-channel-写阻塞没有消费者)
  - [6.3 for-range 读取未关闭的 Channel](#63-for-range-读取未关闭的-channel)
  - [6.4 Select 等待永远不会发生的事件](#64-select-等待永远不会发生的事件)
  - [6.5 HTTP / RPC 请求没有超时](#65-http--rpc-请求没有超时)
  - [6.6 Context 未正确取消](#66-context-未正确取消)
  - [6.7 无限循环没有退出条件](#67-无限循环没有退出条件)
- [7 Go Runtime 如何调度网络 IO？](#7-go-runtime-如何调度网络-io)
- [8 你如何在高并发场景下提高 Go 的吞吐？](#8-你如何在高并发场景下提高-go-的吞吐)
- [9 sync.Pool 的重用原理是什么？什么时候不适合用？](#9-syncpool-的重用原理是什么什么时候不适合用)
- [10 Go 中的内存逃逸如何判断？怎么避免？](#10-go-中的内存逃逸如何判断怎么避免)
- [11 Gin / GoFrame 框架](#11-gin--goframe-框架)

# Golang 面试题
# 1 Goroutine 为什么比线程轻量？实现原理是啥？
Goroutine 比线程轻量主要有三个原因：      
第一，goroutine 初始栈只有 2KB，并且支持动态扩展，而线程默认栈通常是 1MB。      

第二，goroutine 的调度是在 Go runtime 中完成的，是用户态调度，而线程调度需要操作系统参与，涉及用户态和内核态切换。      

第三，goroutine 的上下文切换只需要保存少量寄存器和栈信息，比线程切换成本低很多。      

Go 的 goroutine 是基于 GMP 调度模型实现的，其中：      

G 表示 goroutine      

M 表示操作系统线程      

P 表示调度器      

P 维护 goroutine 的运行队列，M 绑定 P 执行 goroutine，同时调度器通过 work stealing（工作窃取） 实现负载均衡。
# 2 GMP 调度模型
## 2.1 gmp模型 
Goroutine (G)      
      ↓      
Processor (P) 维护 run queue      
      ↓      
Machine (M) 绑定 P      
      ↓      
CPU 执行      
M 必须绑定 P 才能执行 G         
## 2.2 调度流程
一个 goroutine 执行流程：      
1 创建 goroutine   
2 放入 P 的本地队列   ，P1: G1 G2 G3   
3 M 从队列取 G 执行
## 2.3 goroutine发生系统调用阻塞有什么影响？
goroutine 最终必须运行在 M（OS 线程） 上。  

当 goroutine 执行 阻塞系统调用（syscall） 时，比如：  

文件 IO 

网络 IO 

sleep 

DNS 查询  

某些 C 库调用 

此时会发生：  

当前 goroutine 进入 syscall 

执行 goroutine 的 M 被内核阻塞  

如果不处理，P 也会跟着被占用  

问题就来了：  

P 被占住，无法调度新的 goroutine  

CPU 利用率下降  

goroutine 吞吐下降  

## 2.4 如何优化？
### 2.4.1 Go Runtime 如何解决这个问题？
Go Runtime 设计了一套机制来避免 syscall 阻塞调度器。

核心策略是：

syscall 时释放 P

具体流程：

goroutine 调用 syscall

当前 M 进入 syscall 阻塞

runtime 把 P 从这个 M 上解绑

P 重新分配给新的 M

新 M 继续执行 goroutine   
即使某个线程被阻塞，调度器仍然可以继续工作。
### 2.4.2 网络 IO 的进一步优化（netpoll）
工作流程：

goroutine 发起网络 IO

如果数据未就绪

goroutine 被挂起

epoll 等待事件

IO 就绪后唤醒 goroutine

这样：

goroutine 不会占用线程等待 IO。

优点：

大量网络连接只需要少量线程

极大提升并发能力  
### 2.4.3 调度层面的优化
Go Runtime 还有两个重要优化：

1 动态创建 M  

如果没有空闲线程可以接管 P，runtime 会创建新的 M。  

保证 goroutine 可以继续执行。 
2 Work Stealing（工作窃取） 
如果某个 P 没任务了，它会从其他 P 偷任务。   
P1: G1 G2 G3 G4   
P2: empty    
P2 会偷：G3 G4   
这叫Work Stealing，   
优点：
CPU利用率高    
自动负载均衡

## 2.5 如果大量 goroutine 都在 syscall，会发生什么？
如果大量 goroutine 同时进入 syscall，Go runtime 会不断创建新的 M 来接管 P，从而避免调度器停滞。但这样可能导致线程数量膨胀，增加内存消耗和上下文切换开销。因此 Go 对网络 IO 使用 netpoll（epoll/kqueue）实现非阻塞 IO，从而避免大量线程被系统调用阻塞。  
## 2.6 为什么需要P
每个P维护一个队列，减少锁竞争。      
      
## 2.7 GMP 模型中 M 和 P 的关系？为什么需要 work stealing？
P是处理器个数一般与机器cpu核数相同，例如8 核 CPU → 默认 P = 8。 
M 是 **操作系统线程**，数量是 **动态变化的**。go runtime会根据需要创建M，一般来说M >= P     

这叫Work Stealing，   
优点：  
CPU利用率高     
自动负载均衡  
## 2.8 为什么 Go 的 runqueue 长度是 256？
从 调度效率 + cache + 锁竞争 三个角度回答。

第一，先说结论（面试开头一句话）

Go 的每个 P 都有一个 长度为 256 的本地 goroutine 队列（runqueue），这样设计是为了：

减少访问全局队列

减少锁竞争

提高 CPU cache 命中率

提升调度吞吐

第二，避免频繁访问全局队列

如果本地队列太小，例如：

runqueue = 8

那么 goroutine 稍微多一点就会：

本地队列满

goroutine 被放到 global runqueue

这样会导致：

多个线程同时访问 global queue

结果：

全局锁竞争严重。

而 256 的容量可以容纳大量 goroutine，大多数调度都在本地完成。

所以：

访问 global queue 的次数大幅减少。

第三，减少调度器锁竞争

global runqueue 是需要加锁的。

如果 goroutine 经常进入 global queue：

所有线程都会竞争同一把锁。

但本地队列 256 足够大：

大多数 goroutine 都在本地队列运行。

所以：

锁竞争显著减少。

第四，提高 CPU cache 命中率

调度器需要频繁操作 runqueue。

如果队列太大：

会导致：

内存访问增加

cache miss 增加

如果太小：

又会频繁访问 global queue。

256 是 Go runtime 团队经过大量测试后选择的一个 cache-friendly 大小：

数据结构不会太大

大部分操作都在 CPU cache 内完成

因此调度效率更高。

第五，配合 work stealing

当某个 P 的 runqueue 为空时：

它会从其他 P 的 runqueue 偷一半任务。

例如：

P1：0 个 G
P2：200 个 G

P1 会从 P2 偷 100 个 G。

如果 runqueue 太小：

偷不到多少任务。

而 256 的容量可以保证：

窃取效率高

负载均衡更好。

第六，为什么不是 1024 或更大

如果 runqueue 非常大：

例如 4096：

问题会变成：

队列操作变慢

cache miss 增加

goroutine 分布不均

work stealing 成本增加

所以：

256 是 调度效率和内存局部性之间的折中值。 

总结：
Go 的每个 P 都维护一个本地 goroutine 队列，长度是 256。这样设计主要是为了减少对全局队列的访问，从而降低锁竞争。同时本地队列可以提高 CPU cache 命中率，让调度器的大部分操作都在本地完成。另外在 work stealing 时，如果某个 P 空闲，可以从其他 P 的队列偷一半 goroutine，256 的容量可以保证负载均衡效率。这个值是 Go runtime 经过大量性能测试后选择的一个调度效率和内存局部性之间的折中。
# 3 Channel  
## 3.1 为什么 Channel 是线程安全的？ 
channel 内部使用了 mutex 锁 + 等待队列 + runtime 调度。   
当多个 goroutine 同时 ：   
send   
receive   
close       
操作 channel 时，Go runtime 会通过：锁保证 同一时间只有一个 goroutine 修改 channel 内部状态。   
## 3.2 Channel 的底层结构
```golang
type hchan struct {
    qcount   uint           // 队列中元素数量
    dataqsiz uint           // 环形队列大小
    buf      unsafe.Pointer // 环形队列
    elemsize uint16         // 元素大小

    closed   uint32

    sendx    uint           // 发送位置
    recvx    uint           // 接收位置

    recvq    waitq          // 接收等待队列
    sendq    waitq          // 发送等待队列

    lock     mutex          // 互斥锁
}
```
## 3.3 Channel 的核心结构
```
        +----------------+
send →  |                |
        |   RingBuffer   |
recv ←  |                |
        +----------------+

 sendq (等待发送)
 recvq (等待接收)
```
本质是环形队列+ goroutine等待队列   
## 3.4 发送数据时发生了什么 
```
            ch <- value
                 │
                 ▼
        runtime.chansend()
                 │
                 ▼
          获取 channel.lock
                 │
                 ▼
      Channel 是否已经关闭？
           │           │
         YES          NO
           │           │
           ▼           ▼
        panic     recvq 是否有等待接收者？
                         │
                 ┌───────┴────────┐
                 │                │
               YES               NO
                 │                │
                 ▼                ▼
        直接把数据拷贝         buffer 是否有空间？
        给等待的 goroutine           │
           │                ┌───────┴────────┐
           │                │                │
           │               YES              NO
           │                │                │
           ▼                ▼                ▼
        唤醒接收者        写入环形队列        当前 goroutine
                          buf[sendx]        进入 sendq 队列
                          sendx++              │
                                               ▼
                                          gopark 阻塞
``` 
发送数据时其实只有 三种结果：      
### 3.4.1 有等待的接收者 
数据 不经过 buffer, 这是 无缓冲 channel 的核心机制。 直接 G1 (send) ─────► G2 (recv)。
### 3.4.2 buffer 有空间 
数据写入 环形缓冲区。
```golang
        Channel Buffer      

   ┌───────────────────┐      
   │ 1 │ 2 │ 3 │ _ │ _ │      
   └───────────────────┘      
             ↑      
          sendx      
```
### 3.4.3 buffer 满了
发送 goroutine：进入 sendq,    然后gopark()进入阻塞状态。      
示意：      
```
sendq      

G1      
G2      
G3      
```
等待被唤醒      
### 3.4.4 Channel send 的三步判断 总结
1 有 recv 等待 → 直接给 receiver      
2 buffer 有空间 → 写入 buffer      
3 buffer 满 → 进入 sendq 阻塞      
## 3.5 无缓冲 Channel 和带缓冲 Channel 的调度区别？
### 3.5.1 无缓冲调度流程图
```
sendG      
   │      
   ▼      
等待 recvG      
   │      
   ▼      
数据直接拷贝      
   │      
   ▼      
双方继续执行      
```
### 3.5.2 有缓冲channel调度流程
```
sendG
   │
   ▼
写入 buffer
   │
   ▼
sendG 继续执行

  ↓

recvG
   │
   ▼
从 buffer 读取
```
### 3.5.3核心调度区别  
```
| 对比         | 无缓冲 channel     | 有缓冲 channel    |
| ----------   | -------------     | -------------- |
| 是否有 buffer | ❌               | ✅              |
| 通信方式      | 同步             | 异步             |
| 发送是否阻塞   | 必须等接收       | buffer满才阻塞     |
| 调度方式      | goroutine直接交接 | 通过 ring buffer |
| 常见用途      | 协程同步          | 任务队列           |

```
## 3.6 Channel 底层锁竞争如何避免？为什么用了双锁 + ring buffer？
# 4 Map
## 4.1 map为什么不是线程安全的
Go 的 map 默认不是线程安全的，因为 map 的底层结构在写入时会修改 bucket、count 等多个字段，这些操作不是原子操作。如果多个 goroutine 同时写 map，可能导致数据结构损坏。  

另外 Go 的 map 在负载因子超过阈值时会触发扩容，扩容过程中会涉及 bucket 迁移，如果此时有并发写，会破坏内部结构。因此 runtime 会直接检测并发写并 panic。  

Go 之所以没有在 map 内部加锁，是为了保证单线程场景下的性能，如果需要并发安全，一般通过外部加锁或者使用 sync.Map。  
# 5 GC
## 5.1 GC算法是什么   
Go 的 GC 使用 三色标记法。
所有对象初始为 白色，从根对象开始标记为 灰色，处理灰色对象并将它引用的对象继续染灰，处理完变 黑色。
最后仍为白色的对象全部回收。
为了避免并发标记时对象引用变化导致漏标，Go 使用 写屏障，保证新增引用的对象立即标灰。
清理阶段是并发执行，STW 时间极短。   

## 5.2 为什么不会 STW？    
因为 Go 做了一个超级关键的优化：   

Go 有 “写屏障（write barrier）”，让你的程序在运行时主动告诉 GC：对象引用被我改掉啦！

写屏障就像 GC 的“监控器”。

只要你修改指针，GC 立刻知道，并采取动作保证不漏。

# 6 Goroutine 泄漏的场景有哪些？
goroutine 泄漏的本质是 goroutine 被阻塞，无法继续执行，也无法退出。常见包括：channel 阻塞、未关闭 channel、IO 没超时、select 无法满足、context 未取消、死锁或无限循环     
## 6.1 Channel 读阻塞（没有生产者）
当 goroutine 从 channel 读取数据，但没有任何 goroutine 写入数据时，会永久阻塞。

```go
ch := make(chan int)

go func() {
    v := <-ch
    fmt.Println(v)
}()
```
原因  

没有生产者写入数据  

goroutine 永远阻塞在 <-ch 

解决方案  

确保有生产者  

使用 select + timeout 

或关闭 channel  
## 6.2 Channel 写阻塞（没有消费者） 
向无缓冲 channel 写数据时，如果没有消费者读取，就会阻塞。 
```
ch := make(chan int)

go func() {
    ch <- 1
}()
```
原因

无缓冲 channel 需要读写同时存在

没有消费者

解决方案

启动消费者

使用带缓冲 channel

使用 select
## 6.3 for-range 读取未关闭的 Channel 
使用 for range 读取 channel 时，如果 channel 不关闭，循环不会退出。 
```
func worker(ch chan int) {
    for v := range ch {
        fmt.Println(v)
    }
}
```
原因

range channel 只有在 channel 关闭时才会结束。

解决方案

在生产者结束时关闭 channel：

close(ch)
## 6.4 Select 等待永远不会发生的事件
如果 select 监听的 channel 永远不会有数据，goroutine 会永久阻塞。     
```
go func() {
    select {
    case <-ch:
        fmt.Println("data")
    }
}()
```
解决方案

增加超时机制：
```
select {
case <-ch:
case <-time.After(time.Second):
}
```
## 6.5 HTTP / RPC 请求没有超时   
resp, err := http.Get(url) 如果 goroutine 发起网络请求但没有设置超时，可能会一直阻塞。  
解决方案      

使用带超时的 HTTP Client：    
```
client := http.Client{
    Timeout: 5 * time.Second,
}
```
## 6.6 Context 未正确取消
如果 goroutine 依赖 context 退出，但外部没有调用 cancel()，就可能一直等待。 
```
ctx, cancel := context.WithCancel(context.Background())

go func() {
    <-ctx.Done()
}()
```
解决方案  
确保调用：  
cancel()
## 6.7 无限循环没有退出条件
如果 goroutine 中有死循环且没有退出逻辑，会永久运行。
```
go func() {
    for {
        time.Sleep(time.Second)
    }
}()
```
解决方案

使用 context 控制退出：
```
for {
    select {
    case <-ctx.Done():
        return
    default:
    }
}
```
# 7 Go Runtime 如何调度网络 IO？

# 8 你如何在高并发场景下提高 Go 的吞吐？

# 9 sync.Pool 的重用原理是什么？什么时候不适合用？

# 10 Go 中的内存逃逸如何判断？怎么避免？

# 11 Gin / GoFrame 框架

Gin 是如何做到高性能路由匹配的？

中间件的执行顺序是怎么实现的？

GoFrame 的 IOC 容器是怎么做依赖注入的？

Gin 的 Context 是怎么做复用的？

为什么 Gin 不使用反射？带来了什么好处？

如何在 Gin / GoFrame 中实现一个可控制链路超时的 middleware？

高并发下如何减少 context.WithTimeout 的内存分配？

如何封装一个全局错误处理器（panic recover + 错误码 + trace）？

---
