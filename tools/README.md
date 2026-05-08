# Go 线上问题可视化排查脚本

`go_incident_visualizer.py` 用于在 Go 服务线上异常时快速保留现场，并生成一个可视化 HTML 报告，帮助判断问题更可能出在 CPU、内存、goroutine、网络连接、IO 还是下游依赖。

脚本只依赖 Python 标准库，适合直接复制到线上 Linux 机器执行。

## 文件结构

```text
tools/
├── README.md
├── examples/
│   └── bad_go_service.go
└── go_incident_visualizer.py
```

## 代码结构

`go_incident_visualizer.py` 主要分为几块：

- `run_cmd()`：统一执行系统命令，捕获 stdout、stderr、耗时、权限错误和超时。
- `collect_system()`：采集系统现场，包括 `uptime`、`free -m`、`df -h`、`top`、`ps`、`vmstat`、`iostat`。
- `collect_process()`：采集指定 PID 的进程信息，包括 `/proc/<pid>/status`、RSS、线程数、`pmap`。
- `collect_threads()`：采集进程内线程 CPU Top，并自动生成十六进制 TID，用于和 Go goroutine dump 对齐。
- `collect_network()`：通过 `ss -antp` 统计连接状态，如 `ESTAB`、`CLOSE-WAIT`、`TIME-WAIT`、`SYN-SENT`。
- `analyze_goroutine_dump()`：分析 Go dump 文件，统计 goroutine 数量、状态、热点关键词和重复栈帧。
- `score_findings()`：根据采集结果生成问题判断，例如 CPU 打满、goroutine 泄漏、CLOSE-WAIT 过多、DB/HTTP 阻塞。
- `render_html()`：把所有采集结果渲染成单文件 HTML 报告。
- `main()`：解析命令行参数，组织采集、分析和报告输出。

## 基本用法

指定 PID：

```bash
python3 tools/go_incident_visualizer.py --pid 12345 --output report.html
```

按进程名模糊查找 PID：

```bash
python3 tools/go_incident_visualizer.py --process-name your-go-service --output report.html
```

生成后会得到两个文件：

```text
report.html   # 可视化报告
report.json   # 原始采集数据
```

## 分析 goroutine dump

如果已经有 goroutine dump 日志：

```bash
python3 tools/go_incident_visualizer.py \
  --pid 12345 \
  --goroutine-log goroutine.log \
  --output report.html
```

报告会额外展示：

- goroutine 总数
- goroutine 状态分布
- `chan send` / `chan receive` 阻塞数量
- `database/sql`、`net/http`、`sync.Mutex.Lock` 等热点关键词
- 重复栈帧 Top

## 触发 Go goroutine dump

紧急排查时可以让脚本给 Go 进程发送 `SIGQUIT`：

```bash
python3 tools/go_incident_visualizer.py --pid 12345 --send-quit --output report.html
```

注意：

- Go Runtime 会把所有 goroutine 栈打印到进程日志中。
- 默认情况下，Go 进程收到 `SIGQUIT` 后可能会退出；生产环境使用前要确认服务的信号处理方式。
- 如果服务由 systemd 管理，去 `journalctl -u 服务名` 查。
- 如果服务跑在 Kubernetes 中，去 `kubectl logs pod名` 查。
- 拿到 dump 后，再用 `--goroutine-log` 重新跑一次，报告会更完整。

如果服务已经暴露了 pprof，更推荐用安全方式导出 goroutine：

```bash
curl 'http://127.0.0.1:6060/debug/pprof/goroutine?debug=2' > goroutine.log
```

## 常见排查结果解释

### 单线程 CPU 接近打满

报告中会显示类似：

```text
TID 12388 / 0x3064 当前 CPU 99.5%
```

处理方式：

1. 触发 goroutine dump。
2. 在 dump 中搜索十六进制线程 ID，例如 `3064`。
3. 根据栈帧定位死循环、空 `select default`、无限重试或日志疯狂打印。

### goroutine 数量异常

如果 goroutine 数量达到几万甚至几十万，通常要优先排查：

- channel 阻塞
- 下游 HTTP / RPC 阻塞
- 数据库连接池耗尽
- 队列生产速度大于消费速度
- context 没有正确取消

### CLOSE-WAIT 过多

通常说明连接没有被正确关闭，优先检查：

```go
defer resp.Body.Close()
```

### SYN-SENT 过多

通常说明下游不可达，优先检查：

- DNS
- 网络 ACL
- 防火墙
- 下游服务状态
- 超时配置

### IO wait 高

如果 `vmstat` 中 `wa` 高，说明请求慢不一定是 CPU 问题，可能是磁盘 IO 卡住或日志写入过重。

## 建议执行流程

1. 先生成基础报告：

```bash
python3 tools/go_incident_visualizer.py --pid 12345 --output report.html
```

2. 如果 CPU 高，触发 goroutine dump：

```bash
python3 tools/go_incident_visualizer.py --pid 12345 --send-quit --output report.html
```

3. 从服务日志中保存 dump：

```bash
journalctl -u your-service -n 1000 > goroutine.log
```

4. 结合 dump 生成完整报告：

```bash
python3 tools/go_incident_visualizer.py \
  --pid 12345 \
  --goroutine-log goroutine.log \
  --output report.html
```

## 权限说明

部分采集项依赖系统权限：

- `/proc/<pid>/status`
- `ps -L`
- `ss -antp`
- `pmap`

如果权限不足，脚本不会直接崩溃，而是在报告中保留错误信息。线上排查时建议使用服务所属用户或具备足够权限的运维账号执行。

## 注意事项

- 脚本不会自动重启或修改线上服务。
- `--send-quit` 会发送 Go dump 信号，默认 Go 进程可能会打印堆栈后退出；生产环境谨慎使用。
- 报告中的判断是启发式规则，最终仍需要结合业务日志、发布记录、下游状态和代码变更确认根因。
- 如果线上服务已经接入 pprof / Prometheus / trace，应结合这些工具一起判断。

## 使用示例故障程序测试

仓库内提供了一个故意写坏的 Go 服务：

```text
tools/examples/bad_go_service.go
```

启动服务：

```bash
go run tools/examples/bad_go_service.go
```

另开一个终端触发故障：

```bash
curl 'http://127.0.0.1:18080/cpu?n=4'
curl 'http://127.0.0.1:18080/leak?n=3000'
curl 'http://127.0.0.1:18080/mem?mb=128'
curl 'http://127.0.0.1:18080/block?n=300'
curl 'http://127.0.0.1:18080/debug/goroutines' > /tmp/goroutine.log
```

生成排查报告：

```bash
python3 tools/go_incident_visualizer.py \
  --process-name bad_go_service \
  --goroutine-log /tmp/goroutine.log \
  --output /tmp/bad_go_report.html
```

示例程序包含的问题：

- `/cpu`：启动空循环 goroutine，模拟 CPU 飙升。
- `/leak`：启动大量永远阻塞在 channel receive 的 goroutine，模拟 goroutine 泄漏。
- `/mem`：分配并持有大块内存，模拟内存上涨。
- `/block`：启动大量长时间睡眠 goroutine，模拟请求堆积。
- `/debug/goroutines`：安全导出 goroutine dump，便于脚本分析。
