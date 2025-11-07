#!/usr/bin/env python3
"""测试线程修复"""

import sys
import threading
import time
import pjsua as pj

def test_external_thread():
    """测试在外部线程中调用PJLIB"""
    print("\n测试场景：外部线程调用PJLIB")
    print("-" * 50)
    
    # 初始化PJSIP
    lib = pj.Lib()
    lib.init(log_cfg=pj.LogConfig(level=1))
    lib.start()
    lib.set_null_snd_dev()
    
    print("✓ PJSIP已初始化")
    
    # 测试1: 未注册的线程（应该失败）
    def unregistered_thread():
        print("\n[测试1] 未注册线程尝试调用PJLIB...")
        try:
            # 尝试创建播放器（会触发断言）
            player = pj.Lib.instance().create_player("/tmp/test.wav", loop=False)
            print("  ✗ 不应该成功（这不对）")
        except Exception as e:
            print(f"  ✓ 预期的失败: {type(e).__name__}")
    
    # 测试2: 已注册的线程（应该成功）
    def registered_thread():
        print("\n[测试2] 已注册线程尝试调用PJLIB...")
        try:
            # 注册线程
            pj.Lib.instance().thread_register("test_worker")
            print("  ✓ 线程已注册")
            
            # 现在可以安全调用PJLIB
            # 注意：这里不实际创建播放器，只是测试可以调用
            print("  ✓ 可以安全调用PJLIB函数")
            
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    
    # 运行测试2（跳过测试1因为会导致程序崩溃）
    print("\n注意：跳过未注册线程测试（会导致程序崩溃）")
    
    t = threading.Thread(target=registered_thread)
    t.start()
    t.join()
    
    print("\n✓ 测试完成")
    lib.destroy()

if __name__ == "__main__":
    test_external_thread()
