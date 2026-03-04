import requests
import time
import concurrent.futures

BASE = "http://localhost:8090"

def make_call(phone):
    resp = requests.post(f"{BASE}/api/call", json={
        "phone_number": phone,
        "audio_file": "test.wav"
    })
    data = resp.json()
    print(f"  拨打 {phone}: success={data.get('success')}, call_id={data.get('call_id', data.get('error', ''))[:8]}")
    return data

# 1. 并发发起 5 个呼叫
print("=== 并发拨打 5 个号码 ===")
# phones = [f"821210654{i}" for i in range(5)]
phonelist = ["10001", "62085711398700", "62082283631218", "628161668810", "62081381607730"]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(make_call, phonelist))

success_count = sum(1 for r in results if r.get("success"))
print(f"\n成功发起: {success_count} / {len(phonelist)}")

# 2. 轮询状态
print("\n=== 监控通话状态 ===")
for _ in range(30):
    time.sleep(2)
    status = requests.get(f"{BASE}/api/status").json()
    active = status.get("active_calls", 0)
    print(f"  活跃通话: {active}")
    if active == 0:
        print("  所有通话已结束")
        break

# 3. 检查 CDR
print("\n=== 检查 CDR 记录 ===")
today = time.strftime("%Y%m%d")
cdr = requests.get(f"{BASE}/api/cdr?date={today}").json()
print(f"  今日通话记录数: {cdr.get('count', 0)}")
for rec in cdr.get("records", [])[-5:]:
    print(f"    {rec['call_id'][:8]}... → {rec.get('callee_raw','')} "
          f"disposition={rec['disposition']} talk={rec.get('duration_talk',0)}s "
          f"played={rec.get('ivr_play_completed',False)}")