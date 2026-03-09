# 进入pod命令
kubectl -n namesapce exec -it pod bash 
# 过滤pod中的日志
kubectl get pods -n namespace | grep -E "^pod-" | awk '{ print $1}' | xargs -I {} kubectl exec -it -n namespace {} -- bash -c 'echo {}; cd /home/project/logs; egrep "/user/login" log_info.log | egrep "99999999"  '
# 查看pod详细信息
kubectl describe pods -owide service-333eeeee-9679t -n namespace
# 查看service信息
kubectl -n namespace get service wps-service -owide
kubectl -n namespace describe service wps-service
# k8s知识点总结
https://blog.csdn.net/MssGuo/article/details/125267817?ops_request_misc=&request_id=&biz_id=102&utm_term=k8s%E9%9D%A2%E8%AF%95%E9%A2%98&utm_medium=distribute.pc_search_result.none-task-blog-2~all~sobaiduweb~default-0-125267817.nonlogin&spm=1018.2226.3001.4187 
