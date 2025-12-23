# 1 优化http router 
主要手段   
## 1. 减少栈帧与锁的延迟调用
```
func (a *Agent) withRLock(fn func(cc Connector)) {
	a.rw.RLock()
	cc := a.connector
	a.rw.RUnlock()
	fn(cc)
}
优化为
func (a *Agent) getConnector() Connector {
	a.rw.RLock()
	v := a.connector
	a.rw.RUnlock()
	return v
}

函数调用方式以前是 
func (a *Agent) setLogContextFunc(ctx context.Context) {
	a.withRLock(func(cc Connector) { // 栈帧1: setLogContextFunc
		if slc, ok := cc.(nethelp.SetLogContext); ok {
			slc.SetLogContext(ctx)
		} // 栈帧2: withRLock
	})  // 栈帧3: 匿名func调用
}

函数调用方式现在是
func (a *Agent) setLogContextFunc(ctx context.Context) {
	if slc, ok := a.getConnector().(nethelp.SetLogContext); ok { // 栈帧1: getConnector() 
		slc.SetLogContext(ctx)
	}
}

```
## 2. 优化编译-内联/struct内存对齐   
```
// 优化规则：从大字节到小字节排列字段
// 16字节：interface{}, string
// 1-2字节：FieldType, Level

// 坏：小字段在前，大字段在后
type field struct {
    a byte    // 1字节 + 7字节填充
    b byte    // 1字节 + 7字节填充
    c string  // 16字节
    d interface{} // 16字节
} // 总大小: 48字节

// 好：大字段在前，小字段在后  
type field struct {
    d interface{} // 16字节
    c string      // 16字节
    a byte        // 1字节
    b byte        // 1字节
    // 6字节填充
} // 总大小: 40字节
```
性能影响：     
1. 内存减少          
假设有100万个field对象：     
优化前：100万 × 48字节 = 48MB     
优化后：100万 × 40字节 = 40MB     
节省：8MB内存     
2. 缓存友好性     
CPU缓存行通常64字节     
优化前：一个field可能跨越多条缓存行     
优化后：一个field更可能完整装入缓存行     
3. GC压力     
更小的结构体 = 更少的内存分配     
GC扫描和标记更快
## 3 log日志打印写磁盘优化
1 打印日志中的json数据转换为|格式分割，减少数据存储空间；      
2 多次写文件，改为聚合够一定数量一次性写文件，减少磁盘io次数      
3 
```
var emptybytesStr =[]byte("")

func strToBytes(str string) (bs []byte) {
	if len(str) == 0 {
		return emptybytesStr
	}
	strHdr := (*reflect.StringHeader)(unsafe.Pointer(&str))
	sliceHdr := (*reflect.SliceHeader)(unsafe.Pointer(&bs))
	sliceHdr.Data = strHdr.Data
	sliceHdr.Cap = strHdr.Len
	sliceHdr.Len = strHdr.Len

	return bs
}

e.write(key, []byte(val)) 改为  e.write(key, strToBytes(val))
```
// Go 1.20+ 推荐写法
```
func str2BytesV2(s string) []byte {
    return unsafe.Slice(unsafe.StringData(s), len(s))
}
```
优化的核心：     
消除内存分配：避免[]byte()的堆分配   
消除内存复制：避免O(n)的数据复制   
减少GC压力：不产生新的垃圾对象   
代价：   
安全性降低：绕过类型安全检查   
使用约束：返回的切片必须只读   
维护成本：需要开发者理解底层原理   
## 4 优化锁的粒度
### 4.1 拆分大锁为小锁-分段锁
```
// ❌ 不好：整个map一个锁
type Cache struct {
    mu    sync.RWMutex
    items map[string]interface{}
}

func (c *Cache) Get(key string) interface{} {
    c.mu.RLock()          // 全局锁，所有操作串行
    defer c.mu.RUnlock()
    return c.items[key]
}

func (c *Cache) Set(key string, val interface{}) {
    c.mu.Lock()           // 阻塞所有读操作
    defer c.mu.Unlock()
    c.items[key] = val
}
```
优化后
```
// ✅ 好：分为多个桶，每个桶独立锁
type Shard struct {
    sync.RWMutex
    items map[string]interface{}
}

type ConcurrentMap struct {
    shards []*Shard
    count  int // 桶数量，通常为2的幂
}

func NewConcurrentMap(shardCount int) *ConcurrentMap {
    shards := make([]*Shard, shardCount)
    for i := range shards {
        shards[i] = &Shard{items: make(map[string]interface{})}
    }
    return &ConcurrentMap{shards: shards, count: shardCount}
}

// 哈希函数决定key在哪个桶
func (m *ConcurrentMap) getShard(key string) *Shard {
    hash := fnv.New32a()
    hash.Write([]byte(key))
    return m.shards[hash.Sum32()%uint32(m.count)]
}

func (m *ConcurrentMap) Get(key string) interface{} {
    shard := m.getShard(key)  // 只锁这一个桶
    shard.RLock()
    defer shard.RUnlock()
    return shard.items[key]   // 其他桶的操作不受影响
}

func (m *ConcurrentMap) Set(key string, val interface{}) {
    shard := m.getShard(key)  // 只锁这一个桶
    shard.Lock()
    defer shard.Unlock()
    shard.items[key] = val
}
```
### 4.2 读写场景下，互斥锁改为读写锁，读的允许并发读
### 4.3 细粒度对象锁, 优化前：整个结构体一把锁
```
// ❌ 不好：一个锁保护所有字段
type UserService struct {
    mu      sync.RWMutex
    users   map[int]*User
    config  Config
    stats   Stats
    cache   map[string]interface{}
}

func (s *UserService) UpdateUser(id int, user *User) {
    s.mu.Lock()                     // 锁住整个服务
    s.users[id] = user              // 更新users
    s.stats.TotalUpdates++          // 更新stats
    s.mu.Unlock()                   // 其他无关字段也被锁
}
```
优化后
```
// ✅ 好：每个资源独立锁
type UserService struct {
    userMu  sync.RWMutex
    users   map[int]*User
    
    configMu sync.RWMutex
    config  Config
    
    statsMu sync.Mutex
    stats   Stats
    
    cacheMu sync.RWMutex
    cache   map[string]interface{}
}

func (s *UserService) UpdateUser(id int, user *User) {
    s.userMu.Lock()           // 只锁users
    s.users[id] = user
    s.userMu.Unlock()
    
    s.statsMu.Lock()          // 只锁stats
    s.stats.TotalUpdates++
    s.statsMu.Unlock()        // 其他操作可并发执行
}
```
### 4.4 使用sync.Map替代手动锁
```
// ❌ 不好：手动管理并发
type SafeMap struct {
    mu sync.RWMutex
    m  map[string]interface{}
}

func (s *SafeMap) Store(key string, value interface{}) {
    s.mu.Lock()
    s.m[key] = value
    s.mu.Unlock()
}
```
优化后
```
// ✅ 好：使用标准库优化实现
type SafeMap struct {
    m sync.Map  // 内部自动优化锁粒度
}

func (s *SafeMap) Store(key string, value interface{}) {
    s.m.Store(key, value)  // 内部使用更细粒度的锁
}

func (s *SafeMap) Load(key string) (interface{}, bool) {
    return s.m.Load(key)   // 读优化
}
```
# 5 优化golang GC
Go程序的GC会对性能有较大影响，若机器内存足够大，可以通过修改GOGC参数来调整GC的频率(减少GC次数)，从而实现性能优化的目的。   
具体GOGC的值调整为多少，需要结合实际情况（如服务已用内存、机器可用内存、服务接口耗时分布情况等) 
# 6 高并发下如何减少 context.WithTimeout 的内存分配？
在高并发下，减少 context.WithTimeout 内存分配的核心思路只有三类：    

1 能不创建就不创建    

2 把 timeout 上移 / 复用   

3 用更轻量的超时控制手段代替   

下面逐条展开，都是实战中能明显降 alloc 的办法。   
context.WithTimeout 为什么“贵”？

每次调用它，至少会产生：

一个新的 timerCtx 结构体（逃逸到堆）

一个 time.Timer（内部有 heap 对象）

一个 Done() channel

一次 goroutine 调度关联（timer 触发）

👉 在 QPS 很高的链路里，alloc + GC 压力非常明显    
## 6.1 1 最有效的优化手段   
把 WithTimeout 上移到入口层 。而不是 在 每一层 / 每一次 RPC / 每一次 DB 调用都建 timeout。   

错误做法：   
```
func dao(ctx context.Context) error {
    ctx, cancel := context.WithTimeout(ctx, 50*time.Millisecond)
    defer cancel()
    ...
}
```

正确做法：   只在请求入口建一次   

```
func handler(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 200*time.Millisecond)
    defer cancel()

    service(ctx)
    dao(ctx)
}

底层只用ctx形参
func dao(ctx context.Context) error {
    select {
    case <-ctx.Done():
        return ctx.Err()
    default:
    }
}

```




