# 智能打断快速参考

## 🎯 问题
打断太灵敏：用户说"嗯"、"哦"或背景杂音就打断TTS播放

## ✅ 解决方案
智能打断系统 - 三层过滤：VAD长度 + ASR识别 + LLM语义判断

## 📝 配置

```python
CONFIG = {
    'smart_interrupt_enabled': True,          # 启用智能打断 ✅
    'interrupt_min_frames': 10,               # 最少10帧(300ms)
    'interrupt_check_semantic': True,         # LLM语义检查 ✅
}
```

## 🔄 工作流程

```
用户说话 → VAD检测
    ↓
≥ 300ms? → 快速ASR识别
    ↓
"eh/um/ya" → 忽略 ✅
"saya mau tanya" → 打断! ✅
```

## 📊 过滤规则

### 自动忽略
- **太短** (≤2字符): "eh", "um", "ya"
- **填充词**: "eh", "em", "um", "uh", "ah", "hmm"
- **简短回应**: "ya", "iya", "oh", "ok", "oke", "baik"

### LLM判断（可选）
- **YES**: 新问题、新陈述 → 打断
- **NO**: 确认词、杂音 → 忽略

## 🚀 测试

```bash
./call_optimized.sh <电话号码>
```

启动时显示：
```
智能打断: 已启用 (最少10帧, LLM语义:启用)
```

### 测试场景

| 用户输入 | 预期结果 |
|---------|---------|
| "eh" | ✅ 继续播放 |
| "um" | ✅ 继续播放 |
| "ya" | ✅ 继续播放 |
| "oke" | ✅ 继续播放 |
| "saya mau tanya" | ✅ 停止播放 |
| "tunggu dulu" | ✅ 停止播放 |
| 咳嗽声 | ✅ 继续播放 |
| 背景噪音 | ✅ 继续播放 |

## 📝 日志示例

### 忽略打断
```
[打断检查] 快速ASR识别中... 'eh' → 忽略 (填充词(eh))
[打断检查] 快速ASR识别中... 'ya' → 忽略 (简短回应(ya))
```

### 触发打断
```
[打断检查] 快速ASR识别中... 'saya mau tanya' → 打断! (LLM判断:有打断意图)
```

## ⚙️ 调优

### 太灵敏？增加帧数
```python
'interrupt_min_frames': 15,  # 从10改到15 (450ms)
```

### 太迟钝？减少帧数
```python
'interrupt_min_frames': 5,   # 从10改到5 (150ms)
```

### 降低成本？禁用LLM
```python
'interrupt_check_semantic': False,  # 仅关键词过滤
```

### 传统模式？
```python
'smart_interrupt_enabled': False,  # 立即打断
```

## 💰 成本

- **ASR**: ~$0.0001/次（450ms音频）
- **LLM**: ~$0.0005/次（5 tokens）
- **总计**: ~$0.0006/次打断检查

## 📊 推荐配置

| 场景 | smart_interrupt | min_frames | check_semantic |
|------|----------------|-----------|---------------|
| **生产环境** ✅ | True | 10 | True |
| 快速响应 | True | 5 | False |
| 严格过滤 | True | 15 | True |
| 传统模式 | False | - | - |

## 📚 详细文档

`SMART_INTERRUPT_GUIDE.md` - 完整指南和原理说明
