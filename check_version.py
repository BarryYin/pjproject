#!/usr/bin/env python3
"""检查 OptimizedNLSASREngine 的属性"""

import sys
sys.path.insert(0, '/home/henry/pjproject/alibabacloud-nls-python-sdk')

# 从文件导入
exec(open('/home/henry/pjproject/sip_ai_nls_optimized.py').read(), globals())

# 创建实例
print("正在创建 OptimizedNLSASREngine 实例...")
try:
    asr = OptimizedNLSASREngine()
    print(f"✅ min_interval = {asr.min_interval}")
    print(f"✅ error_count = {asr.error_count}")
    print(f"✅ max_errors = {asr.max_errors}")
    print("\n所有属性都已正确初始化！")
except AttributeError as e:
    print(f"❌ 错误: {e}")
    print("\n属性未初始化！")
except Exception as e:
    print(f"⚠ 其他错误: {e}")
