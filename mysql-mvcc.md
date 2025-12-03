# 1 mvcc是什么？  
MySQL的MVCC（多版本并发控制）是一种数据库并发控制技术，用于提高数据库的并发性能   
# 2 mvcc解决了什么问题？
读写并发性能问题，也是提交读和可重复读的解决方案，实现数据一致性的方案    
# 3 mvcc实现原理   
通过innodb行的隐藏列（trx_id、roll_pointer）+ undo log（多个版本串成链）+ read view这3个组合决定一行记录的哪个版本对当前事务可见，从而避免加锁，实现非阻塞读   
## 3.1 innodb隐藏列   
| 隐藏列              | 作用                      |
| ---------------- | ----------------------- |   
| **trx_id**       | 最近一次修改该行的事务 ID          |   
| **roll_pointer** | 指向 Undo Log 的指针，用来找到旧版本 |   

## 3.2 undo log    
当一行更新时：   
UPDATE user SET age = 20 WHERE id = 1   
InnoDB 会：   
1 把旧值写入 Undo Log   
2 在主记录上写入新的 trx_id   
3 row 隐藏字段 roll_pointer 指向 Undo Log   
4 如果事务反复更新，Undo Log 形成一个版本链：   
5 最新版本 → 上一个版本 → 上一个版本 → ...   
## 3.3 read view   
每个 read-view 中保存：
m_ids：读视图创建时，当前系统里所有活跃的事务 ID
min_trx_id：m_ids 最小值
max_trx_id：系统已分配的下一个事务 ID     
# 4 举例子说明实物可见性是怎么工作的     
## 4.1 构造数据版本链     
假设一行数据被更新2次     
-- 初始插入   
trx_id = 50:  name="A"   

-- 更新 1    
trx_id = 80:  name="B"   

-- 更新 2（最新）   
trx_id = 99:  name="C"   
形成的 版本链（最新在最上）     
当前记录（主记录）  
┌最新版本 (trx_id=99)   
     ↓   
上一版本 (trx_id=80)   
     ↓   
再上一版本 (trx_id=50)      

roll_pointer 这就是“99 → 80 → 50”的历史链。   

## 4.2 read view 判断流程图（决定到底看到哪个版本）   
假设你当前事务生成的 ReadView：   

m_ids（活跃事务并且未提交） = [90, 93, 99]   

min_trx_id = 90   

max_trx_id = 100   

开始快照读时：   
先选取历史链上的第一个版本号位99的在read view中进行比较：   
99 在 m_ids 中所以不可见。   继续沿 roll_pointer 走到下一版本   
然后选择第二个版本链80在read view中比较：   
80 < min_trx_id=90    可见   
所以事务看到的就是 trx_id=80 的版本   
# 5 事物id与read view比较口诀
判断一个版本是否对当前事务可见：   

如果 trx_id < min_trx_id   
→ 此事务在 ReadView 创建前已提交    
→ 可见   

如果 trx_id ∈ m_ids   
→ 此事务正在执行   
→ 不可见   

如果 trx_id ≥ max_trx_id   
→ 此事务在 ReadView 后才开始   
→ 不可见   

其余情况   
→ 表示事务已提交   
→ 可见   

📌口诀：   
小于 min 或者 不在m_ids中都是可见的，其他都是不可见的  

