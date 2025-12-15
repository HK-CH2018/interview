# 为什么只有值传递 
一句话先给结论：Java 只有值传递，没有引用传递。   
## 基本类型：最容易理解
```
public static void main(String[] args) {
    int a = 10;
    change(a);
    System.out.println(a); // 输出10，并没有改变为20
}

static void change(int x) {
    x = 20;
}
```
## 对象类型：迷惑就从这里开始
```
public static void main(String[] args) {
    Person p = new Person("Tom");
    change(p);
    System.out.println(p.name); // 输出Jerry，看起来是改变了P里边的数据，这是为什么呢？
}

static void change(Person p2) {
    p2.name = "Jerry";
}

```
## 关键认知：对象变量里存的是什么？
```
Person p = new Person("Tom");
```
p存的是对象的地址，0x123456   
p本身不是对象，是一个地址值    
方法调用时到底传了什么？change（p）
```
main:   
p  -> 0x1234   
change:   
p2 -> 0x1234   
```
把 0x1234 这个“地址值”复制一份 → 给 p2 ,p2也是 0x1234  
所以为什么能改成功？     
p2 和 p, 指向 同一个对象, 改的是对象内部内容   
👉 不是 p 被改了
👉 是对象里的内容被改了   
## 关键反例：彻底证明不是引用传递
```
public static void main(String[] args) {
    Person p = new Person("Tom");
    change(p);
    System.out.println(p.name); // 输出Tom,而不是Jerry，如果是引用传递，此处p2会改变实参p的值，应该是Jerry。
}

static void change(Person p2) {
    p2 = new Person("Jerry");
}

p  -> 0x1234 (Tom)
p2 -> 0x1234

p2 = new Person("Jerry")
p2 -> 0x5678 (Jerry)

```
## 给你一个“永不混淆”的判断口诀
记住一句话：能不能在方法里，让外面的变量指向一个新对象？   
❌ 不能 → 值传递（Java）
✅ 能 → 引用传递（C++）

# 结论
Java 只有值传递，对象参数传递的是引用值的拷贝；   
C++ 支持引用传递，可以在函数中直接修改外部变量本身。
