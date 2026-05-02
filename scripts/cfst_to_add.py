#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 CloudflareSpeedTest 的结果目录合并后转成本项目可用的 ADD.txt。"""

from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from pathlib import Path


LOCATIONS_URL = "https://speed.cloudflare.com/locations"


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
    speed = speed.strip()
    if not speed:
        return ""
    try:
        value = float(speed)
        return f"{value:g}"
    except Exception:
        return speed.replace("MB/s", "").strip()


def load_locations() -> dict[str, dict[str, str]]:
    try:
        with urllib.request.urlopen(LOCATIONS_URL, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        mapping: dict[str, dict[str, str]] = {}
        for item in data:
            iata = str(item.get("iata", "")).strip().upper()
            if not iata:
                continue
            mapping[iata] = {
                "city": str(item.get("city", "")).strip(),
                "cca2": str(item.get("cca2", "")).strip().upper(),
                "region": str(item.get("region", "")).strip(),
            }
        return mapping
    except Exception:
        return {}


COUNTRY_MAP = {
    "HK": "香港",
    "TW": "台湾",
    "JP": "日本",
    "KR": "韩国",
    "SG": "新加坡",
    "TH": "泰国",
    "MY": "马来西亚",
    "PH": "菲律宾",
    "ID": "印度尼西亚",
    "VN": "越南",
    "IN": "印度",
    "AU": "澳大利亚",
    "NZ": "新西兰",
    "US": "美国",
    "CA": "加拿大",
    "MX": "墨西哥",
    "BR": "巴西",
    "CL": "智利",
    "GB": "英国",
    "FR": "法国",
    "DE": "德国",
    "NL": "荷兰",
    "ES": "西班牙",
    "IT": "意大利",
    "CH": "瑞士",
    "AT": "奥地利",
    "SE": "瑞典",
    "DK": "丹麦",
    "PL": "波兰",
    "CZ": "捷克",
    "TR": "土耳其",
    "AE": "阿联酋",
    "QA": "卡塔尔",
    "ZA": "南非",
}


def build_remark(colo: str, speed: str, locations: dict[str, dict[str, str]]) -> str:
    colo = colo.strip().upper()
    speed_text = normalize_speed(speed)
    if colo and colo != "N/A" and colo in locations:
        item = locations[colo]
        country = COUNTRY_MAP.get(item.get("cca2", ""), item.get("cca2", ""))
        city = item.get("city", "")
        location = country or colo
        if city:
            location = f"{location}-{city}"
    else:
        location = colo or "CF优选"
    return f"{location}{speed_text}MB/s" if speed_text else location


def iter_csv_files(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        return sorted(p for p in input_path.glob("*.csv") if p.is_file())
    return [input_path]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="result.csv 或结果目录")
    parser.add_argument("--output", required=True, help="输出 ADD.txt")
    parser.add_argument("--merged-output", default="", help="合并后的 result.csv 输出路径")
    parser.add_argument("--port", default="443", help="节点端口")
    parser.add_argument("--top", type=int, default=60, help="输出前 N 个")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    merged_output = Path(args.merged_output) if args.merged_output else None
    if not input_path.exists():
        raise SystemExit(f"输入不存在: {input_path}")

    locations = load_locations()
    files = iter_csv_files(input_path)
    if not files:
        raise SystemExit("没有找到任何 csv 结果文件")

    dedup: dict[str, tuple[float, float, str, dict[str, str]]] = {}
    merged_rows: list[dict[str, str]] = []
    for file in files:
        with file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = pick(row, ["IP 地址", "IP地址", "IP", "ip"])
                if not ip:
                    continue
                delay = pick(row, ["平均延迟", "平均延迟(ms)", "延迟", "延迟(ms)"])
                speed = pick(row, ["下载速度(MB/s)", "下载速度", "速度(MB/s)"])
                colo = pick(row, ["地区码", "数据中心", "地区", "colo", "COLO"])

                speed_val = to_float(speed)
                delay_val = to_float(delay, 999999)
                merged_rows.append(row)

                # 只保留有效结果：有地区码且速度大于 0
                if speed_val <= 0 or not colo or colo.upper() == "N/A":
                    continue

                remark = build_remark(colo, speed, locations)
                line = f"{ip}:{args.port}#{remark}"
                old = dedup.get(ip)
                # 优先速度高，其次延迟低
                candidate = (speed_val, -delay_val, line, row)
                if old is None or candidate[:2] > old[:2]:
                    dedup[ip] = candidate

    ranked = sorted(dedup.values(), key=lambda x: (x[0], x[1]), reverse=True)
    lines = [item[2] for item in ranked[: args.top]]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    if merged_output:
        merged_output.parent.mkdir(parents=True, exist_ok=True)
        if merged_rows:
            fieldnames = list(merged_rows[0].keys())
            with merged_output.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(merged_rows)

    if not lines:
        raise SystemExit("没有生成任何有效优选 IP，请检查测速结果或条件。")


if __name__ == "__main__":
    main()
