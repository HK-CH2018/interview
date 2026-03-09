# 微服务 / 云原生面试题

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

---

# 7 Docker / K8s / CICD
中级题

# 7.1 Docker 镜像分层是怎么实现的？

# 7.2 为什么生产环境不建议 root 用户跑容器？

## 7.3 Kubernetes service 的流量转发机制？
ClusterIP（默认类型）,仅在集群内部可访问 ,转发机制是 通过 kube-proxy 维护 iptables/ipvs 规则，负载均衡到后端 Pod（默认轮询）   
NodePort ，外部访问：通过任意节点的 IP + 端口访问    
LoadBalancer，云平台集成：自动创建云负载均衡器    
实现机制：      
kube-proxy 的工作模式：    
1. iptables 模式   
2. ipvs（默认）    
   

# 7.4 Deployment 滚动更新流程？

# 7.5 K8s 如何处理 Pod crash？

高级题

# 7.6 你如何设计无损发布？

# 7.7 K8s 中如何实现自动扩容（HPA）？

# 7.8 Pod 网络模型（CNI）是如何通信的？

# 7.9 StatefulSet 为什么适合有状态服务？

# 7.10 如何排查集群中 CPU Throttle 问题？

---

8️⃣ Prometheus + Grafana
中级题

# 8.1 Prometheus 的 Pull 模型优势是什么？

# 8.2 Counter / Gauge / Histogram / Summary 区别？

# 8.3 什么是 P99？如何计算？

# 8.4 PromQL 如何写一个 QPS 查询？

# 8.5 如何监控 Goroutine、GC、Heap？

高级题

# 8.6 如何实现全链路 Trace？

# 8.7 如何构建一个 SLO + SLA 体系？

# 8.8 Grafana 如何与 Loki/Tempo 联合使用？

# 8.9 如何做报警的抖动防抖？

