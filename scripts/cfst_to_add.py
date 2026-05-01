#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 CloudflareSpeedTest 的 result.csv 转成本项目可用的 ADD.txt。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


# 常见 Cloudflare 数据中心码映射。未列出的会保留原始地区码。
COLO_COUNTRY = {
    "HKG": "香港",
    "TPE": "台湾",
    "NRT": "日本",
    "KIX": "日本",
    "ICN": "韩国",
    "SIN": "新加坡",
    "BKK": "泰国",
    "KUL": "马来西亚",
    "MNL": "菲律宾",
    "CGK": "印度尼西亚",
    "HAN": "越南",
    "SGN": "越南",
    "DEL": "印度",
    "BOM": "印度",
    "MAA": "印度",
    "SYD": "澳大利亚",
    "MEL": "澳大利亚",
    "AKL": "新西兰",
    "LAX": "美国",
    "SJC": "美国",
    "SEA": "美国",
    "DFW": "美国",
    "ORD": "美国",
    "IAD": "美国",
    "EWR": "美国",
    "JFK": "美国",
    "ATL": "美国",
    "MIA": "美国",
    "YVR": "加拿大",
    "YYZ": "加拿大",
    "MEX": "墨西哥",
    "GRU": "巴西",
    "SCL": "智利",
    "LHR": "英国",
    "MAN": "英国",
    "CDG": "法国",
    "FRA": "德国",
    "AMS": "荷兰",
    "MAD": "西班牙",
    "BCN": "西班牙",
    "MXP": "意大利",
    "FCO": "意大利",
    "ZRH": "瑞士",
    "VIE": "奥地利",
    "ARN": "瑞典",
    "CPH": "丹麦",
    "WAW": "波兰",
    "PRG": "捷克",
    "IST": "土耳其",
    "DXB": "阿联酋",
    "DOH": "卡塔尔",
    "JNB": "南非",
}


def pick(row: dict[str, str], candidates: list[str]) -> str:
    for key in candidates:
        if key in row and row[key].strip():
            return row[key].strip()
    return ""


def to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip().replace("%", ""))
    except Exception:
        return default


def normalize_speed(speed: str) -> str:
    """统一速度显示，避免 20.00 显示得太长。"""
    speed = speed.strip()
    if not speed:
        return ""
    try:
        value = float(speed)
        return f"{value:g}"
    except Exception:
        return speed.replace("MB/s", "").strip()


def build_remark(colo: str, speed: str, country: str = "") -> str:
    """生成简洁节点名，例如：香港20MB/s。"""
    colo = colo.strip().upper()
    location = country.strip() or COLO_COUNTRY.get(colo, "") or colo or "CF优选"
    speed_text = normalize_speed(speed)
    return f"{location}{speed_text}MB/s" if speed_text else location


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CloudflareSpeedTest result.csv")
    parser.add_argument("--output", required=True, help="输出 ADD.txt")
    parser.add_argument("--port", default="443", help="节点端口")
    parser.add_argument("--top", type=int, default=20, help="输出前 N 个")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        raise SystemExit(f"输入文件不存在: {input_path}")

    rows: list[tuple[float, float, str]] = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip = pick(row, ["IP 地址", "IP地址", "IP", "ip"])
            if not ip:
                continue

            delay = pick(row, ["平均延迟", "平均延迟(ms)", "延迟", "延迟(ms)"])
            speed = pick(row, ["下载速度(MB/s)", "下载速度", "速度(MB/s)"])
            colo = pick(row, ["地区码", "数据中心", "地区", "colo", "COLO"])
            country = pick(row, ["国家", "国家/地区", "country", "Country"])

            remark = build_remark(colo, speed, country)
            line = f"{ip}:{args.port}#{remark}"

            # 优先速度高，其次延迟低。
            rows.append((to_float(speed), -to_float(delay, 999999), line))

    rows.sort(reverse=True)
    lines = [line for _, _, line in rows[: args.top]]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    if not lines:
        raise SystemExit("没有生成任何优选 IP，请检查 result.csv 或调低筛选条件。")


if __name__ == "__main__":
    main()

