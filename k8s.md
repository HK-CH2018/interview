# 进入pod命令
kubectl -n namesapce exec -it pod bash 
# 过滤pod中的日志
kubectl get pods -n namespace | grep -E "^pod-" | awk '{ print $1}' | xargs -I {} kubectl exec -it -n namespace {} -- bash -c 'echo {}; cd /home/project/logs; egrep "/user/login" log_info.log | egrep "99999999"  '
# 查看pod详细信息
kubectl describe pods -owide service-333eeeee-9679t -n namespace
# 查看service信息
kubectl -n namespace get service wps-service -owide
kubectl -n namespace describe service wps-service
