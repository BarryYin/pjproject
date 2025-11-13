# PJSIP Call ID 断言失败问题修复

## 错误信息

```
python: ../src/pjsua-lib/pjsua_call.c:2718: pjsua_call_get_user_data: 
Assertion `call_id>=0 && call_id<(int)pjsua_var.ua_cfg.max_calls' failed.
Aborted (core dumped)
```

## 问题原因

这个错误发生在以下场景：

1. **多线程访问呼叫对象** - 当一个线程正在访问`call.info()`时，呼叫可能已在另一个线程中结束
2. **呼叫已失效但仍被访问** - 呼叫结束后，`call_id`变为无效值，但代码仍尝试访问
3. **没有进行有效性检查** - 直接调用`call.info()`而不检查`call.is_valid()`

## 问题代码示例

```python
# 错误的做法 ❌
def input_thread_func(call_obj):
    while call_obj.get('active', False):
        current_call = call_obj.get('call')
        if current_call:
            # 危险！没有检查呼叫是否有效
            info = current_call.info()  # 可能导致断言失败
            print(info.state_text)
```

```python
# 主循环中的错误做法 ❌
while True:
    # 危险！呼叫可能已失效
    if current_call.info().state == pj.CallState.DISCONNECTED:
        break
```

## 解决方案

### 1. 始终检查呼叫有效性

```python
# 正确的做法 ✓
def input_thread_func(call_obj):
    while call_obj.get('active', False):
        current_call = call_obj.get('call')
        if current_call:
            # 首先检查呼叫是否有效
            if not current_call.is_valid():
                print("呼叫已失效")
                continue
            
            try:
                info = current_call.info()
                print(info.state_text)
            except Exception as e:
                print(f"访问失败: {e}")
```

### 2. 使用异常处理保护

```python
# 正确的做法 ✓
while True:
    try:
        # 检查有效性
        if not current_call or not current_call.is_valid():
            print("呼叫已失效")
            break
        
        # 安全访问
        if current_call.info().state == pj.CallState.DISCONNECTED:
            print("呼叫已结束")
            break
            
    except Exception as e:
        print(f"状态检查异常: {e}")
        break
```

### 3. 使用线程锁保护

```python
# 最佳实践 ✓
class SafeCallCallback(pj.CallCallback):
    def __init__(self, call=None):
        pj.CallCallback.__init__(self, call)
        self.lock = threading.Lock()
    
    def is_call_valid(self):
        """线程安全的有效性检查"""
        try:
            with self.lock:
                if not self.call:
                    return False
                if not self.call.is_valid():
                    return False
                return True
        except:
            return False
    
    def on_state(self):
        """线程安全的状态处理"""
        try:
            if not self.is_call_valid():
                return
            
            with self.lock:
                info = self.call.info()
                # 处理状态...
        except Exception as e:
            print(f"状态回调异常: {e}")
```

### 4. 清理时的安全检查

```python
# 正确的清理方式 ✓
finally:
    if current_call:
        try:
            # 检查是否有效
            if current_call.is_valid():
                info = current_call.info()
                if info.state != pj.CallState.DISCONNECTED:
                    print("挂断呼叫...")
                    current_call.hangup()
                    time.sleep(1)
        except Exception as e:
            print(f"清理异常（忽略）: {e}")
            pass
```

## 修复后的代码对比

### 修复前（会崩溃）

```python
# 危险代码
if current_call.info().state == pj.CallState.DISCONNECTED:
    break
```

### 修复后（安全）

```python
# 安全代码
try:
    if not current_call or not current_call.is_valid():
        break
    
    if current_call.info().state == pj.CallState.DISCONNECTED:
        break
except Exception as e:
    print(f"检查异常: {e}")
    break
```

## 关键要点

### ✓ 必须做的

1. **始终检查 `is_valid()`** - 在访问呼叫对象之前
2. **使用异常处理** - 包装所有呼叫访问
3. **多线程使用锁** - 保护共享的呼叫对象
4. **清理时检查** - finally块中也要检查有效性

### ✗ 不要做的

1. **直接访问 `call.info()`** - 不检查有效性
2. **假设呼叫始终有效** - 呼叫可能随时结束
3. **忽略异常** - 记录并处理所有异常
4. **跨线程不加保护访问** - 使用锁或队列

## 测试验证

使用修复后的代码：

```bash
# 使用修复后的原始脚本
python3 sip_test_call_indonesia.py 81234567890

# 或使用安全版本
python3 test_call_safe.py 81234567890
```

## 调试技巧

如果仍遇到问题：

1. **降低日志级别**
   ```python
   LOG_LEVEL = 5  # 最详细的日志
   ```

2. **添加调试信息**
   ```python
   print(f"[DEBUG] call.is_valid() = {current_call.is_valid()}")
   print(f"[DEBUG] call object = {current_call}")
   ```

3. **使用GDB调试**
   ```bash
   gdb --args python3 sip_test_call_indonesia.py 81234567890
   (gdb) run
   # 崩溃时输入
   (gdb) bt  # 查看堆栈
   ```

## 相关文件

- ✅ **已修复**: `sip_test_call_indonesia.py` - 原始文件已更新
- ✅ **安全版本**: `test_call_safe.py` - 简化的安全实现
- 📖 **本文档**: `CALL_ID_ASSERTION_FIX.md`

## 总结

这个问题的根本原因是**在呼叫对象失效后仍尝试访问**。解决方案是：

1. 访问前检查 `is_valid()`
2. 使用异常处理保护
3. 多线程环境使用锁
4. 清理时也要检查有效性

按照这些原则，可以完全避免 `call_id` 断言失败的问题。
