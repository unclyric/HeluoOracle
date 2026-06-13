#!/usr/bin/env python3
"""河洛天衍 — 紫微斗数精确排盘计算器

基于 iztro-py 库，输入生辰信息，输出精确的十二宫星曜分布数据。
输出 JSON 格式，与河洛天衍前端兼容。

用法:
    python3 calculate_chart.py --solar 1991-8-15 --hour 1 --gender 男
    python3 calculate_chart.py --lunar 1991-7-6 --hour 1 --gender 男 --leap
    python3 calculate_chart.py --solar 1991-8-15 --hour 1 --gender 男 --output chart.json
"""

import argparse
import json
import sys

from iztro_py import astro

# ── 地支映射 ──────────────────────────────────────────────
BRANCH_CN = {
    "ziEarthly": "子",
    "chouEarthly": "丑",
    "yinEarthly": "寅",
    "maoEarthly": "卯",
    "chenEarthly": "辰",
    "siEarthly": "巳",
    "wuEarthly": "午",
    "weiEarthly": "未",
    "shenEarthly": "申",
    "youEarthly": "酉",
    "xuEarthly": "戌",
    "haiEarthly": "亥",
}

# ── 天干映射 ──────────────────────────────────────────────
STEM_CN = {
    "jiaHeavenly": "甲",
    "yiHeavenly": "乙",
    "bingHeavenly": "丙",
    "dingHeavenly": "丁",
    "wuHeavenly": "戊",
    "jiHeavenly": "己",
    "gengHeavenly": "庚",
    "xinHeavenly": "辛",
    "renHeavenly": "壬",
    "guiHeavenly": "癸",
}

# ── 五行局映射 ────────────────────────────────────────────
FIVE_ELEMENTS_CN = {
    "water2": "水二局",
    "wood3": "木三局",
    "metal4": "金四局",
    "earth5": "土五局",
    "fire6": "火六局",
}

# ── 四化映射 ──────────────────────────────────────────────
MUTAGEN_CN = {"禄": "化禄", "权": "化权", "科": "化科", "忌": "化忌"}

# ── 时辰映射 ──────────────────────────────────────────────
HOUR_NAMES = {
    0: "早子时 (23:00-00:00)",
    1: "丑时 (01:00-03:00)",
    2: "寅时 (03:00-05:00)",
    3: "卯时 (05:00-07:00)",
    4: "辰时 (07:00-09:00)",
    5: "巳时 (09:00-11:00)",
    6: "午时 (11:00-13:00)",
    7: "未时 (13:00-15:00)",
    8: "申时 (15:00-17:00)",
    9: "酉时 (17:00-19:00)",
    10: "戌时 (19:00-21:00)",
    11: "亥时 (21:00-23:00)",
    12: "晚子时 (23:00-00:00)",
}

# ── 宫位名称（按命宫为起点的顺序） ──────────────────────
PALACE_NAMES = [
    "命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
    "迁移", "交友", "官禄", "田宅", "福德", "父母",
]


def translate_name(obj):
    """安全获取星辰/宫位的中文名"""
    if hasattr(obj, "translate_name"):
        return obj.translate_name()
    return str(obj)


def build_chart(
    date_str: str,
    hour_index: int,
    gender: str,
    is_lunar: bool = False,
    is_leap: bool = False,
    language: str = "zh-CN",
) -> dict:
    """构建完整的紫微斗数命盘数据

    Args:
        date_str: 日期字符串，格式 YYYY-M-D
        hour_index: 时辰索引 0=早子 1=丑 ... 11=亥 12=晚子
        gender: 性别 "男" 或 "女"
        is_lunar: 是否为农历日期
        is_leap: 是否为闰月（仅农历有效）
        language: 输出语言

    Returns:
        命盘数据字典，包含：宫位信息、星曜分布、四化、五行局等
    """
    # ── 排盘 ──────────────────────────────────────────
    if is_lunar:
        chart = astro.by_lunar(date_str, hour_index, gender, is_leap, True, language)
    else:
        chart = astro.by_solar(date_str, hour_index, gender, language)

    # ── 命宫/身宫 ─────────────────────────────────────
    soul_idx = chart.get_soul_palace().index
    body_idx = chart.get_body_palace().index

    # ── 五行局 ────────────────────────────────────────
    fec = chart.five_elements_class
    five_elements = FIVE_ELEMENTS_CN.get(fec, fec)
    # 提取局数
    ju_number = int("".join(c for c in five_elements if c.isdigit()) or "5")

    # ── 生年四化 ─────────────────────────────────────
    year_mutagens = []
    for p in chart.palaces:
        for s in list(p.major_stars) + list(p.minor_stars):
            if hasattr(s, "mutagen") and s.mutagen:
                year_mutagens.append(
                    {
                        "star": translate_name(s),
                        "mutagen": MUTAGEN_CN.get(s.mutagen, s.mutagen),
                        "palace": translate_name(p),
                        "branch": BRANCH_CN.get(p.earthly_branch, p.earthly_branch),
                    }
                )

    # ── 十二宫数据 ────────────────────────────────────
    palaces = []
    for p in chart.palaces:
        major = [translate_name(s) for s in p.major_stars]
        minor = [translate_name(s) for s in p.minor_stars]
        adj = (
            [translate_name(s) for s in p.adjective_stars]
            if hasattr(p, "adjective_stars")
            else []
        )

        # 宫位内星辰的四化
        star_mutagens = []
        for s in list(p.major_stars) + list(p.minor_stars):
            if hasattr(s, "mutagen") and s.mutagen:
                star_mutagens.append(
                    {"star": translate_name(s), "mutagen": s.mutagen}
                )

        # 大限信息
        dec = p.decadal
        decadal_range = f"{dec.range[0]}-{dec.range[1]}" if dec else ""
        decadal_stem = (
            STEM_CN.get(dec.heavenly_stem, dec.heavenly_stem) if dec else ""
        )
        decadal_branch = (
            BRANCH_CN.get(dec.earthly_branch, dec.earthly_branch) if dec else ""
        )

        is_empty = not major
        tags = []
        if p.index == soul_idx:
            tags.append("命宫")
        if p.index == body_idx:
            tags.append("身宫")

        palace_data = {
            "index": p.index,
            "name": translate_name(p),
            "heavenly_stem": STEM_CN.get(p.heavenly_stem, p.heavenly_stem),
            "earthly_branch": BRANCH_CN.get(p.earthly_branch, p.earthly_branch),
            "dizhi": STEM_CN.get(p.heavenly_stem, "")
            + BRANCH_CN.get(p.earthly_branch, ""),
            "major_stars": major,
            "minor_stars": minor,
            "adjective_stars": adj[:5],
            "mutagens": star_mutagens,
            "is_empty": is_empty,
            "decadal_range": decadal_range,
            "decadal_dizhi": decadal_stem + decadal_branch,
            "tags": tags,
        }
        palaces.append(palace_data)

    # ── 空宫 ──────────────────────────────────────────
    empty_palaces_result = (
        chart.empty_palaces()
        if callable(getattr(chart, "empty_palaces", None))
        else []
    )
    empty_palaces = [
        BRANCH_CN.get(ep.earthly_branch, str(ep)) for ep in empty_palaces_result
    ]

    # ── 紫微/天府位置 ─────────────────────────────────
    ziwei_branch = None
    tianfu_branch = None
    for p in chart.palaces:
        for s in p.major_stars:
            name = translate_name(s)
            if name == "紫微":
                ziwei_branch = BRANCH_CN.get(p.earthly_branch, p.earthly_branch)
            if name == "天府":
                tianfu_branch = BRANCH_CN.get(p.earthly_branch, p.earthly_branch)

    # ── 年干支 ────────────────────────────────────────
    chinese_date = chart.chinese_date
    year_stem = chinese_date[0] if len(chinese_date) >= 2 else ""
    year_branch = chinese_date[1] if len(chinese_date) >= 2 else ""
    year_ganzhi = year_stem + year_branch

    # ── 阴阳性别 ─────────────────────────────────────
    stem_index = list(STEM_CN.values()).index(year_stem) if year_stem in STEM_CN.values() else 0
    yinyang = "阳" if stem_index % 2 == 0 else "阴"
    yinyang_gender = yinyang + ("男" if gender == "男" else "女")

    return {
        # 基础信息
        "solar_date": date_str if not is_lunar else chart.solar_date,
        "lunar_date": date_str if is_lunar else chart.lunar_date,
        "chinese_date": chinese_date,
        "gender": gender,
        "hour_index": hour_index,
        "hour_name": HOUR_NAMES.get(hour_index, ""),
        "year_ganzhi": year_ganzhi,
        "year_stem": year_stem,
        "year_branch": year_branch,
        "yinyang_gender": yinyang_gender,
        # 五行局
        "five_elements": five_elements,
        "ju_number": ju_number,
        # 命宫/身宫
        "soul_palace_index": soul_idx,
        "soul_palace_branch": BRANCH_CN.get(
            chart.earthly_branch_of_soul_palace,
            chart.earthly_branch_of_soul_palace,
        ),
        "body_palace_index": body_idx,
        "body_palace_branch": BRANCH_CN.get(
            chart.earthly_branch_of_body_palace,
            chart.earthly_branch_of_body_palace,
        ),
        # 紫微/天府位置
        "ziwei_branch": ziwei_branch,
        "tianfu_branch": tianfu_branch,
        # 四化
        "year_mutagens": year_mutagens,
        # 空宫
        "empty_palaces": empty_palaces,
        # 十二宫详细数据
        "palaces": palaces,
    }


def chart_to_frontend_format(chart_data: dict) -> dict:
    """将 iztro-py 排盘结果转换为河洛天衍前端格式

    前端期望的数据结构：
    - mingPos: 命宫地支索引
    - shenPos: 身宫地支索引
    - allStars: { 地支索引: [星辰名...] }
    - fourHua: { 科/权/禄/忌: 星辰名 }
    - info: { yearGanZhi, yearGan, yearZhi, ju, wuxing, yinyangGender, ... }
    """
    branch_to_idx = {v: k for k, v in enumerate(
        ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    )}

    # 命宫/身宫地支索引
    ming_branch = chart_data["soul_palace_branch"]
    shen_branch = chart_data["body_palace_branch"]
    ming_pos = branch_to_idx.get(ming_branch, 0)
    shen_pos = branch_to_idx.get(shen_branch, 0)

    # 所有星辰
    all_stars = {}
    for p in chart_data["palaces"]:
        branch = p["earthly_branch"]
        idx = branch_to_idx.get(branch, -1)
        if idx == -1:
            continue
        stars = p["major_stars"] + p["minor_stars"]
        if stars:
            all_stars[idx] = stars

    # 四化
    four_hua = {}
    for m in chart_data["year_mutagens"]:
        mut_type = m["mutagen"]  # "化禄", "化权", "化科", "化忌"
        short = mut_type.replace("化", "")  # "禄", "权", "科", "忌"
        four_hua[short] = m["star"]

    # 基本信息
    info = {
        "yearGanZhi": chart_data["year_ganzhi"],
        "yearGan": chart_data["year_stem"],
        "yearZhi": chart_data["year_branch"],
        "ju": chart_data["ju_number"],
        "wuxing": chart_data["five_elements"][0],  # 第一个字：水/木/金/土/火
        "yinyangGender": chart_data["yinyang_gender"],
        "gender": chart_data["gender"],
        "ziweiPos": branch_to_idx.get(chart_data.get("ziwei_branch", ""), 0),
        "tianfuPos": branch_to_idx.get(chart_data.get("tianfu_branch", ""), 0),
        "laiyinPos": _get_laiyin_pos(chart_data["year_stem"]),
    }

    return {
        "mingPos": ming_pos,
        "shenPos": shen_pos,
        "allStars": all_stars,
        "fourHua": four_hua,
        "info": info,
        "palaces": chart_data["palaces"],
    }


def _get_laiyin_pos(year_gan: str) -> int:
    """来因宫位置（以年干定宫位地支索引）"""
    LAIYIN = {"甲": 10, "乙": 9, "丙": 8, "丁": 7, "戊": 6,
              "己": 5, "庚": 4, "辛": 3, "壬": 0, "癸": 11}
    return LAIYIN.get(year_gan, 2)


def main():
    parser = argparse.ArgumentParser(description="河洛天衍 — 紫微斗数精确排盘")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--solar", help="阳历日期，格式 YYYY-M-D")
    group.add_argument("--lunar", help="农历日期，格式 YYYY-M-D")
    parser.add_argument(
        "--hour", type=int, required=True,
        help="时辰索引: 0=早子 1=丑 2=寅 ... 11=亥 12=晚子",
    )
    parser.add_argument("--gender", required=True, choices=["男", "女"])
    parser.add_argument("--leap", action="store_true", help="农历闰月（仅 --lunar 有效）")
    parser.add_argument("--output", help="输出文件路径（默认 stdout）")
    parser.add_argument(
        "--frontend",
        action="store_true",
        help="输出河洛天衍前端兼容格式（供 JS 直接加载）",
    )

    args = parser.parse_args()

    is_lunar = args.lunar is not None
    date_str = args.lunar if is_lunar else args.solar

    chart = build_chart(date_str, args.hour, args.gender, is_lunar, args.leap)

    if args.frontend:
        output_data = chart_to_frontend_format(chart)
    else:
        output_data = chart

    output = json.dumps(output_data, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"排盘数据已写入: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
