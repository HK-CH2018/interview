- [Golang 面试题](#golang-面试题)
- [1 Go：Goroutine、Channel、GMP 调度模型](#1-gogoroutinechannelgmp-调度模型)
  - [1.3 gmp模型](#13-gmp模型)
    - [1.3.1 调度流程](#131-调度流程)
    - [1.3.2 Work Stealing（工作窃取）](#132-work-stealing工作窃取)
    - [1.3.3 系统调用阻塞问题](#133-系统调用阻塞问题)
    - [1.3.4 网络 IO 的优化](#134-网络-io-的优化)
    - [1.3.5 为什么需要P](#135-为什么需要p)
- [2 Goroutine 为什么比线程轻量？实现原理是啥？](#2-goroutine-为什么比线程轻量实现原理是啥)
- [3 Channel 为什么是线程安全的？底层结构是什么？](#3-channel-为什么是线程安全的底层结构是什么)
  - [3.1 为什么 Channel 是线程安全的？](#31-为什么-channel-是线程安全的)
  - [3.2 Channel 的底层结构](#32-channel-的底层结构)
  - [3.3 Channel 的核心结构](#33-channel-的核心结构)
  - [3.4 发送数据时发生了什么](#34-发送数据时发生了什么)
    - [3.4.1 有等待的接收者](#341-有等待的接收者)
    - [3.4.2 buffer 有空间](#342-buffer-有空间)
    - [3.4.3 buffer 满了](#343-buffer-满了)
    - [3.4.4 Channel send 的三步判断 总结](#344-channel-send-的三步判断-总结)
- [4 无缓冲 Channel 和带缓冲 Channel 的调度区别？](#4-无缓冲-channel-和带缓冲-channel-的调度区别)
  - [4.1 无缓冲调度流程图](#41-无缓冲调度流程图)
  - [4.2 有缓冲channel调度流程](#42-有缓冲channel调度流程)
  - [4.3核心调度区别](#43核心调度区别)
- [5 defer 为什么会有性能开销？](#5-defer-为什么会有性能开销)
- [6 Go 的 map 为什么并发不安全？](#6-go-的-map-为什么并发不安全)
- [7 GC 三色标记算法怎么工作？为什么不会 STW？](#7-gc-三色标记算法怎么工作为什么不会-stw)
- [8 为什么不会 STW？](#8-为什么不会-stw)
- [9 Goroutine 泄漏的场景有哪些？](#9-goroutine-泄漏的场景有哪些)
- [10 GMP 模型中 M 和 P 的关系？为什么需要 work stealing？](#10-gmp-模型中-m-和-p-的关系为什么需要-work-stealing)
- [11 Go 调度器如何避免全局锁？](#11-go-调度器如何避免全局锁)
- [12 阻塞系统调用对 GMP 的影响？如何优化？](#12-阻塞系统调用对-gmp-的影响如何优化)
- [13 Go Runtime 如何调度网络 IO？](#13-go-runtime-如何调度网络-io)
- [14 Channel 底层锁竞争如何避免？为什么用了双锁 + ring buffer？](#14-channel-底层锁竞争如何避免为什么用了双锁--ring-buffer)
- [15 你如何在高并发场景下提高 Go 的吞吐？](#15-你如何在高并发场景下提高-go-的吞吐)
- [16 sync.Pool 的重用原理是什么？什么时候不适合用？](#16-syncpool-的重用原理是什么什么时候不适合用)
- [17 Go 中的内存逃逸如何判断？怎么避免？](#17-go-中的内存逃逸如何判断怎么避免)
- [18   Gin / GoFrame 框架](#18---gin--goframe-框架)

# Golang 面试题
# 1 Go：Goroutine、Channel、GMP 调度模型
## 1.3 gmp模型 
Goroutine (G)      
      ↓      
Processor (P) 维护 run queue      
      ↓      
Machine (M) 绑定 P      
      ↓      
CPU 执行      
M 必须绑定 P 才能执行 G         
### 1.3.1 调度流程
一个 goroutine 执行流程：      
1 创建 goroutine   
2 放入 P 的本地队列   ，P1: G1 G2 G3   
3 M 从队列取 G 执行
### 1.3.2 Work Stealing（工作窃取）
如果某个 P 没任务了，它会从其他 P 偷任务。   
P1: G1 G2 G3 G4   
P2: empty    
P2 会偷：G3 G4   
这叫Work Stealing，   
优点：
CPU利用率高    
自动负载均衡
### 1.3.3 系统调用阻塞问题
如果 goroutine 执行：系统调用(read/write), 线程可能被阻塞。Go runtime 会：解绑 P 
M 被阻塞   
P 解绑   
P 找新的 M    
这样其他 goroutine 继续执行。   
### 1.3.4 网络 IO 的优化   
使用epoll优化goroutine的io     
goroutine 发起 IO
↓   
挂起   
↓   
epoll 监听   
↓   
IO完成
↓   
唤醒 goroutine        
这样线程不会被阻塞。      
### 1.3.5 为什么需要P
每个P维护一个队列，减少锁竞争。      
# 2 Goroutine 为什么比线程轻量？实现原理是啥？
Goroutine 比线程轻量主要有三个原因：      
第一，goroutine 初始栈只有 2KB，并且支持动态扩展，而线程默认栈通常是 1MB。      

第二，goroutine 的调度是在 Go runtime 中完成的，是用户态调度，而线程调度需要操作系统参与，涉及用户态和内核态切换。      

第三，goroutine 的上下文切换只需要保存少量寄存器和栈信息，比线程切换成本低很多。      

Go 的 goroutine 是基于 GMP 调度模型实现的，其中：      

G 表示 goroutine      

M 表示操作系统线程      

P 表示调度器      

P 维护 goroutine 的运行队列，M 绑定 P 执行 goroutine，同时调度器通过 work stealing（工作窃取） 实现负载均衡。      

# 3 Channel 为什么是线程安全的？底层结构是什么？ 
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
# 4 无缓冲 Channel 和带缓冲 Channel 的调度区别？
## 4.1 无缓冲调度流程图
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
## 4.2 有缓冲channel调度流程
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
## 4.3核心调度区别  
```
| 对比         | 无缓冲 channel     | 有缓冲 channel    |
| ----------   | -------------     | -------------- |
| 是否有 buffer | ❌               | ✅              |
| 通信方式      | 同步             | 异步             |
| 发送是否阻塞   | 必须等接收       | buffer满才阻塞     |
| 调度方式      | goroutine直接交接 | 通过 ring buffer |
| 常见用途      | 协程同步          | 任务队列           |

```
# 5 defer 为什么会有性能开销？

# 6 Go 的 map 为什么并发不安全？
Go 的 map 默认不是线程安全的，因为 map 的底层结构在写入时会修改 bucket、count 等多个字段，这些操作不是原子操作。如果多个 goroutine 同时写 map，可能导致数据结构损坏。  

另外 Go 的 map 在负载因子超过阈值时会触发扩容，扩容过程中会涉及 bucket 迁移，如果此时有并发写，会破坏内部结构。因此 runtime 会直接检测并发写并 panic。  

Go 之所以没有在 map 内部加锁，是为了保证单线程场景下的性能，如果需要并发安全，一般通过外部加锁或者使用 sync.Map。  
# 7 GC 三色标记算法怎么工作？为什么不会 STW？   
Go 的 GC 使用 三色标记法。
所有对象初始为 白色，从根对象开始标记为 灰色，处理灰色对象并将它引用的对象继续染灰，处理完变 黑色。
最后仍为白色的对象全部回收。
为了避免并发标记时对象引用变化导致漏标，Go 使用 写屏障，保证新增引用的对象立即标灰。
清理阶段是并发执行，STW 时间极短。   

# 8 为什么不会 STW？    
因为 Go 做了一个超级关键的优化：   

Go 有 “写屏障（write barrier）”，让你的程序在运行时主动告诉 GC：对象引用被我改掉啦！

写屏障就像 GC 的“监控器”。

只要你修改指针，GC 立刻知道，并采取动作保证不漏。

# 9 Goroutine 泄漏的场景有哪些？

# 10 GMP 模型中 M 和 P 的关系？为什么需要 work stealing？

# 11 Go 调度器如何避免全局锁？

# 12 阻塞系统调用对 GMP 的影响？如何优化？

# 13 Go Runtime 如何调度网络 IO？

# 14 Channel 底层锁竞争如何避免？为什么用了双锁 + ring buffer？

# 15 你如何在高并发场景下提高 Go 的吞吐？

# 16 sync.Pool 的重用原理是什么？什么时候不适合用？

# 17 Go 中的内存逃逸如何判断？怎么避免？

# 18   Gin / GoFrame 框架

Gin 是如何做到高性能路由匹配的？

中间件的执行顺序是怎么实现的？

GoFrame 的 IOC 容器是怎么做依赖注入的？

Gin 的 Context 是怎么做复用的？

为什么 Gin 不使用反射？带来了什么好处？

如何在 Gin / GoFrame 中实现一个可控制链路超时的 middleware？

高并发下如何减少 context.WithTimeout 的内存分配？

如何封装一个全局错误处理器（panic recover + 错误码 + trace）？

---
