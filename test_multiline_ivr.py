import requests
import time
import concurrent.futures

BASE = "http://localhost:8090"

# 号码 → 音频 配对，每个号码可以播放不同的音频文件
CALL_LIST = [
    {"phone_number": "10001",            "audio_file": "test.wav"},
    {"phone_number": "62085711398700",   "audio_file": "T0.wav"},
    {"phone_number": "62082283631218",   "audio_file": "T0.wav"},
    {"phone_number": "628161668810",     "audio_file": "TL.wav"},
    {"phone_number": "62081381607730",   "audio_file": "TL.wav"},
]

def make_call(task):
    phone = task["phone_number"]
    audio = task["audio_file"]
    try:
        resp = requests.post(f"{BASE}/api/call", json=task, timeout=10)
        data = resp.json()
        print(f"  拨打 {phone} ({audio}): success={data.get('success')}, "
              f"call_id={data.get('call_id', data.get('error', ''))[:8]}")
        return data
    except requests.ConnectionError:
        print(f"  拨打 {phone}: 连接失败，请确认 IVR 服务已启动 (python sip_ivr_simple_api_multiline.py)")
        return {"success": False, "error": "连接失败"}

# 1. 并发发起呼叫
print(f"=== 并发拨打 {len(CALL_LIST)} 个号码 ===")
with concurrent.futures.ThreadPoolExecutor(max_workers=len(CALL_LIST)) as pool:
    results = list(pool.map(make_call, CALL_LIST))

success_count = sum(1 for r in results if r.get("success"))
print(f"\n成功发起: {success_count} / {len(CALL_LIST)}")

# 2. 轮询状态
print("\n=== 监控通话状态 ===")
for _ in range(30):
    time.sleep(2)
    try:
        status = requests.get(f"{BASE}/api/status", timeout=5).json()
        active = status.get("active_calls", 0)
        print(f"  活跃通话: {active}")
        if active == 0:
            print("  所有通话已结束")
            break
    except requests.ConnectionError:
        print("  连接失败，服务可能已停止")
        break

# 3. 检查 CDR
print("\n=== 检查 CDR 记录 ===")
today = time.strftime("%Y%m%d")
try:
    cdr = requests.get(f"{BASE}/api/cdr?date={today}", timeout=5).json()
    print(f"  今日通话记录数: {cdr.get('count', 0)}")
    for rec in cdr.get("records", [])[-5:]:
        print(f"    {rec['call_id'][:8]}... → {rec.get('callee_raw','')} "
              f"disposition={rec['disposition']} talk={rec.get('duration_talk',0)}s "
              f"played={rec.get('ivr_play_completed',False)}")
except requests.ConnectionError:
    print("  连接失败")
