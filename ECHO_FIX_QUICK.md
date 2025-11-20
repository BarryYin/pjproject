# 回声消除快速修复

## 🎯 问题
客户听到回声

## ✅ 解决方案
已启用PJSIP回声消除（AEC）

## 📝 修改内容

**文件**: `sip_ai_nls_optimized.py`

**修改**:
```python
# 之前 ❌
media_cfg.ec_tail_len = 0  # 禁用

# 现在 ✅
media_cfg.ec_tail_len = 400  # 启用，400ms尾长
media_cfg.ec_options = 0     # 使用Speex AEC
media_cfg.no_vad = True      # 使用WebRTC VAD
```

## 🚀 测试

```bash
./call_optimized.sh <电话号码>
```

启动时会显示：
```
回声消除: 已启用 (400ms尾长)
```

## ⚙️ 如果还有回声

### 方案1：增加尾长（处理更长延迟）
```python
media_cfg.ec_tail_len = 800  # 改为800ms
```

### 方案2：降低TTS音量
在 `_play_audio()` 中添加：
```python
pj.Lib.instance().conf_adjust_tx_level(player_slot, 0.7)  # 70%音量
```

### 方案3：增加VAD最小语音长度（过滤回声片段）
```python
CONFIG = {
    'vad_min_speech_frames': 5,  # 从3改到5，150ms最少语音
}
```

## 📊 参数说明

| ec_tail_len | 效果 | CPU |
|-------------|------|-----|
| 0 | ❌ 无 | 最低 |
| 200 | ⭐⭐⭐ | 低 |
| **400** ✅ | ⭐⭐⭐⭐ | 中 |
| 800 | ⭐⭐⭐⭐⭐ | 高 |

**推荐**: 400ms（99%场景适用）

## 🔍 验证方法

1. **扬声器测试** - 使用扬声器（非耳机），应该听不到明显回声
2. **保持安静** - TTS播放时保持安静，看是否误触发VAD
3. **多轮对话** - 进行多次对话，检查回声是否累积

## 📚 详细文档

- `ECHO_CANCELLATION_CONFIG.md` - 完整配置指南
- `OPTIMIZED_VERSION.md` - 系统功能说明
