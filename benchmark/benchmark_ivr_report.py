#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_ivr_report.py - 纯播报型 IVR Benchmark 自动评测报告

从 CDR (logs/cdr/cdr_YYYYMMDD.jsonl) 读取数据，计算 6 项核心指标，
按 base 参考区间做健康判定，输出 Markdown 格式报告。

用法:
  python benchmark/benchmark_ivr_report.py                  # 所有 CDR
  python benchmark/benchmark_ivr_report.py --date 20260303  # 指定日期
  python benchmark/benchmark_ivr_report.py --date 20260301 --date-end 20260307  # 日期范围
"""

import json
import argparse
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CDR_DIR = PROJECT_DIR / "logs" / "cdr"
REPORT_DIR = SCRIPT_DIR / "ivr_reports"

# ────────────────────────────────────────────────────
# Base 参考区间 (来自 Benchmark 文档 §4)
# ────────────────────────────────────────────────────
RATING_LISTEN_THROUGH = [
    (0.45, "很强 ★★★★"),
    (0.30, "不错 ★★★"),
    (0.15, "起步 base ★★"),
    (0.00, "很差 ★"),
]

RATING_EARLY_HANGUP = [
    (0.30, "很强 ★★★★"),
    (0.45, "不错 ★★★"),
    (0.60, "起步 base ★★"),
    (1.01, "很差 ★"),
]

RATING_P50_DURATION = [
    (22, "很强 ★★★★"),
    (15, "不错 ★★★"),
    (10, "起步 base ★★"),
    (0,  "很差 ★"),
]

PASS_LINE = {
    "listen_through": 0.20,
    "early_hangup": 0.55,
    "p50_duration": 12,
}


# ────────────────────────────────────────────────────
# 数据加载
# ────────────────────────────────────────────────────
def load_cdrs(date_filter=None, date_end=None):
    records = []
    if not CDR_DIR.exists():
        print(f"[错误] CDR 目录不存在: {CDR_DIR}")
        return records

    for f in sorted(CDR_DIR.glob("cdr_*.jsonl")):
        file_date = f.stem.replace("cdr_", "")
        if date_filter:
            if date_end:
                if not (date_filter <= file_date <= date_end):
                    continue
            else:
                if file_date != date_filter:
                    continue
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


# ────────────────────────────────────────────────────
# 统计工具
# ────────────────────────────────────────────────────
def percentile(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def pct(num, den):
    return num / den if den > 0 else 0.0


def fmt_pct(v):
    return f"{v * 100:.1f}%"


def rate_listen_through(v):
    for threshold, label in RATING_LISTEN_THROUGH:
        if v >= threshold:
            return label
    return "很差 ★"


def rate_early_hangup(v):
    for threshold, label in RATING_EARLY_HANGUP:
        if v <= threshold:
            return label
    return "很差 ★"


def rate_p50(v):
    for threshold, label in RATING_P50_DURATION:
        if v >= threshold:
            return label
    return "很差 ★"


# ────────────────────────────────────────────────────
# 核心指标计算
# ────────────────────────────────────────────────────
def compute_metrics(records):
    """对一批 CDR 记录计算 Benchmark 指标，返回 dict。"""
    attempts = len(records)
    connected = [r for r in records if r.get("disposition") == "ANSWERED"]
    connects = len(connected)

    durations = [r["duration_talk"] for r in connected if r.get("duration_talk") is not None]

    p50 = percentile(durations, 50)
    p75 = percentile(durations, 75)
    p90 = percentile(durations, 90)

    early = [r for r in connected if r["duration_talk"] < 5]

    partial, listen_through = [], []
    no_L_count = 0
    for r in connected:
        T = r.get("duration_talk", 0)
        L = r.get("ivr_audio_duration", 0)
        if L <= 0:
            no_L_count += 1
            continue
        threshold = 0.9 * L
        if T >= threshold:
            listen_through.append(r)
        elif T >= 5:
            partial.append(r)

    has_L = connects - no_L_count

    return {
        "attempts": attempts,
        "connects": connects,
        "connect_rate": pct(connects, attempts),
        "durations": durations,
        "p50": p50,
        "p75": p75,
        "p90": p90,
        "early_count": len(early),
        "early_rate": pct(len(early), connects),
        "partial_count": len(partial),
        "partial_rate": pct(len(partial), has_L) if has_L > 0 else 0,
        "lt_count": len(listen_through),
        "lt_rate": pct(len(listen_through), has_L) if has_L > 0 else 0,
        "has_L": has_L,
        "no_L_count": no_L_count,
    }


# ────────────────────────────────────────────────────
# 时段分层
# ────────────────────────────────────────────────────
TIME_SLOTS = [
    ("08:00-10:00", 8, 10),
    ("10:00-12:00", 10, 12),
    ("12:00-14:00", 12, 14),
    ("14:00-17:00", 14, 17),
    ("17:00-20:00", 17, 20),
    ("其他", -1, -1),
]


def slot_for_hour(h):
    for label, lo, hi in TIME_SLOTS:
        if lo <= h < hi:
            return label
    return "其他"


def time_slot_breakdown(records):
    buckets = defaultdict(list)
    for r in records:
        ts = r.get("ts_invite_iso") or r.get("ts_invite")
        if not ts:
            buckets["其他"].append(r)
            continue
        try:
            if isinstance(ts, str):
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.fromtimestamp(ts)
            buckets[slot_for_hour(dt.hour)].append(r)
        except Exception:
            buckets["其他"].append(r)
    return buckets


# ────────────────────────────────────────────────────
# 脚本版本分组
# ────────────────────────────────────────────────────
def audio_version_breakdown(records):
    buckets = defaultdict(list)
    for r in records:
        key = r.get("ivr_audio_file") or "unknown"
        buckets[key].append(r)
    return buckets


# ────────────────────────────────────────────────────
# 异常检测 (Benchmark 文档 §7.1)
# ────────────────────────────────────────────────────
def detect_anomalies(m):
    findings = []
    if m["attempts"] > 0 and m["connect_rate"] < 0.15:
        findings.append("Attempt→Connect 率过低 (<15%)：号码质量差 / 主叫信誉差 / 运营商拦截 / 拨打时段不佳")
    if m["connects"] > 0 and m["early_rate"] > 0.60:
        findings.append("Early hang-up 率过高 (>60%)：脚本开头劝退 / 号码被标记 / 用户对催收外呼反感强")
    if m["has_L"] > 0 and m["lt_rate"] < 0.15 and m["early_rate"] <= 0.45:
        findings.append("Listen-through 低但 Early 不高：用户听了一半就挂 → 话术内容、时长、节奏、信息密度问题")
    if m["connects"] > 0 and m["p50"] < 6:
        findings.append("p50 时长很低 (<6s)：大量秒挂或误接通 → 检查号码/振铃设置/接通判定/网络质量")
    return findings


# ────────────────────────────────────────────────────
# 通过线判定 (Benchmark 文档 §9)
# ────────────────────────────────────────────────────
def pass_line_check(m):
    results = []
    if m["has_L"] > 0:
        passed = m["lt_rate"] >= PASS_LINE["listen_through"]
        results.append(("Listen-through ≥ 20%", passed, fmt_pct(m["lt_rate"])))
    else:
        results.append(("Listen-through ≥ 20%", None, "无 L 数据"))
    passed_eh = m["early_rate"] <= PASS_LINE["early_hangup"]
    results.append(("Early hang-up ≤ 55%", passed_eh, fmt_pct(m["early_rate"])))
    passed_p50 = m["p50"] >= PASS_LINE["p50_duration"]
    results.append(("Connected p50 ≥ 12s", passed_p50, f"{m['p50']:.1f}s"))
    return results


# ────────────────────────────────────────────────────
# disposition 分布
# ────────────────────────────────────────────────────
def disposition_breakdown(records):
    counts = defaultdict(int)
    for r in records:
        counts[r.get("disposition", "UNKNOWN")] += 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


# ────────────────────────────────────────────────────
# Markdown 报告生成
# ────────────────────────────────────────────────────
def generate_report(records, title_suffix=""):
    m = compute_metrics(records)

    lines = []

    def w(s=""):
        lines.append(s)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    w(f"# 纯播报型 IVR Benchmark 报告{title_suffix}")
    w()
    w(f"> 生成时间：{now_str}  ")
    w(f"> 数据来源：`{CDR_DIR}`  ")
    w(f"> 总记录数：{len(records)} 条")
    w()

    if not records:
        w("**无 CDR 数据，无法生成报告。**")
        return "\n".join(lines)

    # ── 样本量提示 ──
    if m["attempts"] < 1000:
        w(f"> ⚠️ 当前 Attempt 数为 **{m['attempts']}**，建议至少 1,000–5,000 通才有统计意义。")
        w()

    # ── §1 核心指标总览 ──
    w("---")
    w()
    w("## 1. 核心指标总览")
    w()
    w("| # | 指标 | 数值 | 评级 |")
    w("|---|------|------|------|")
    w(f"| 1 | Attempt→Connect Rate | {fmt_pct(m['connect_rate'])} ({m['connects']}/{m['attempts']}) | — |")
    w(f"| 2 | Connected Duration p50 / p75 / p90 | {m['p50']:.1f}s / {m['p75']:.1f}s / {m['p90']:.1f}s | {rate_p50(m['p50'])} |")
    w(f"| 3 | Early Hang-up Rate (T<5s) | {fmt_pct(m['early_rate'])} ({m['early_count']}/{m['connects']}) | {rate_early_hangup(m['early_rate'])} |")
    if m["has_L"] > 0:
        w(f"| 4 | Partial Listen Rate (5s≤T<0.9L) | {fmt_pct(m['partial_rate'])} ({m['partial_count']}/{m['has_L']}) | — |")
        w(f"| 5 | Listen-through Rate (T≥0.9L) | {fmt_pct(m['lt_rate'])} ({m['lt_count']}/{m['has_L']}) | {rate_listen_through(m['lt_rate'])} |")
    else:
        w("| 4 | Partial Listen Rate | — | 缺少音频时长 L |")
        w("| 5 | Listen-through Rate | — | 缺少音频时长 L |")
    w("| 6 | Complaint / Block Rate | — | 需外部数据 |")
    w()

    if m["no_L_count"] > 0:
        w(f"> ℹ️ 有 {m['no_L_count']} 条接通记录缺少 `ivr_audio_duration`（旧 CDR），Partial/Listen-through 仅基于有 L 的 {m['has_L']} 条计算。")
        w()

    # ── §2 通过线判定 ──
    w("---")
    w()
    w("## 2. 最简通过线判定")
    w()
    w("| 指标 | 通过线 | 实际值 | 结果 |")
    w("|------|--------|--------|------|")
    for label, passed, actual in pass_line_check(m):
        if passed is None:
            icon = "—"
        else:
            icon = "PASS ✅" if passed else "FAIL ❌"
        w(f"| {label} | — | {actual} | {icon} |")
    w()

    # ── §3 分桶分布 ──
    w("---")
    w()
    w("## 3. 接通后通话时长分桶")
    w()
    if m["connects"] > 0:
        w("| 分桶 | 条件 | 数量 | 占比 |")
        w("|------|------|------|------|")
        w(f"| 秒挂/早挂 | T < 5s | {m['early_count']} | {fmt_pct(m['early_rate'])} |")
        if m["has_L"] > 0:
            w(f"| 部分收听 | 5s ≤ T < 0.9L | {m['partial_count']} | {fmt_pct(m['partial_rate'])} |")
            w(f"| 听完 | T ≥ 0.9L | {m['lt_count']} | {fmt_pct(m['lt_rate'])} |")
        else:
            w("| 部分收听 | 5s ≤ T < 0.9L | — | 缺少 L |")
            w("| 听完 | T ≥ 0.9L | — | 缺少 L |")
    else:
        w("无接通记录，跳过。")
    w()

    # ── §4 Disposition 分布 ──
    w("---")
    w()
    w("## 4. 呼叫结果分布 (Disposition)")
    w()
    disp = disposition_breakdown(records)
    w("| Disposition | 数量 | 占比 |")
    w("|------------|------|------|")
    for d, cnt in disp.items():
        w(f"| {d} | {cnt} | {fmt_pct(pct(cnt, m['attempts']))} |")
    w()

    # ── §5 时段分层 ──
    w("---")
    w()
    w("## 5. 时段分层分析")
    w()
    slot_data = time_slot_breakdown(records)
    non_empty_slots = [(label, recs) for label, _, _ in TIME_SLOTS
                       if (recs := slot_data.get(label)) and len(recs) > 0]
    if non_empty_slots:
        w("| 时段 | Attempt | Connect | 接通率 | p50(s) | Early挂断 | 听完率 |")
        w("|------|---------|---------|--------|--------|----------|--------|")
        for label, recs in non_empty_slots:
            sm = compute_metrics(recs)
            lt_str = fmt_pct(sm["lt_rate"]) if sm["has_L"] > 0 else "—"
            w(f"| {label} | {sm['attempts']} | {sm['connects']} | {fmt_pct(sm['connect_rate'])} | {sm['p50']:.1f} | {fmt_pct(sm['early_rate'])} | {lt_str} |")
    else:
        w("无数据或时间信息不可用。")
    w()

    # ── §6 脚本版本对比 ──
    w("---")
    w()
    w("## 6. 脚本版本（音频文件）对比")
    w()
    audio_data = audio_version_breakdown(records)
    if len(audio_data) > 1:
        w("| 音频版本 | Attempt | Connect | 接通率 | p50(s) | Early挂断 | 听完率 |")
        w("|---------|---------|---------|--------|--------|----------|--------|")
        for ver, recs in sorted(audio_data.items()):
            sm = compute_metrics(recs)
            lt_str = fmt_pct(sm["lt_rate"]) if sm["has_L"] > 0 else "—"
            w(f"| {ver} | {sm['attempts']} | {sm['connects']} | {fmt_pct(sm['connect_rate'])} | {sm['p50']:.1f} | {fmt_pct(sm['early_rate'])} | {lt_str} |")
    elif len(audio_data) == 1:
        ver = list(audio_data.keys())[0]
        w(f"仅使用单一音频版本：`{ver}`，无对比数据。")
    else:
        w("无音频版本信息。")
    w()

    # ── §7 异常检测 ──
    w("---")
    w()
    w("## 7. 异常检测与定位建议")
    w()
    anomalies = detect_anomalies(m)
    if anomalies:
        for a in anomalies:
            w(f"- ⚠️ **{a}**")
    else:
        w("未检测到明显异常。")
    w()

    # ── §8 Base 参考区间速查 ──
    w("---")
    w()
    w("## 附录：Base 参考区间")
    w()
    w("| 指标 | 很差 | 起步 base | 不错 | 很强 |")
    w("|------|------|----------|------|------|")
    w("| Listen-through | <15% | 15%–30% | 30%–45% | >45% |")
    w("| Early hang-up | >60% | 45%–60% | 30%–45% | <30% |")
    w("| Partial listen | — | — | 25%–45% (健康) | — |")
    w("| Connected p50 | <6–8s | 10–15s | 15–22s | ≥0.9L |")
    w()

    return "\n".join(lines)


# ────────────────────────────────────────────────────
# 入口
# ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="纯播报型 IVR Benchmark 报告生成器")
    parser.add_argument("--date", type=str, default=None,
                        help="CDR 日期过滤，格式 YYYYMMDD（不指定则读取全部）")
    parser.add_argument("--date-end", type=str, default=None,
                        help="CDR 日期范围结束，格式 YYYYMMDD（配合 --date 使用）")
    parser.add_argument("--output", type=str, default=None,
                        help="输出文件路径（默认自动命名到 benchmark_reports/）")
    parser.add_argument("--stdout", action="store_true",
                        help="仅输出到终端，不保存文件")
    args = parser.parse_args()

    date_label = ""
    if args.date:
        if args.date_end:
            date_label = f"（{args.date} ~ {args.date_end}）"
        else:
            date_label = f"（{args.date}）"

    records = load_cdrs(date_filter=args.date, date_end=args.date_end)
    if not records:
        print(f"[Benchmark] 未找到 CDR 数据{date_label}，目录: {CDR_DIR}")
        return

    print(f"[Benchmark] 加载 {len(records)} 条 CDR 记录{date_label}")
    report = generate_report(records, title_suffix=date_label)

    if args.stdout:
        print(report)
        return

    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_tag = args.date or "all"
        if args.date_end:
            date_tag = f"{args.date}_{args.date_end}"
        out_path = REPORT_DIR / f"benchmark_report_{date_tag}_{ts}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"[Benchmark] ✓ 报告已保存: {out_path}")


if __name__ == "__main__":
    main()
