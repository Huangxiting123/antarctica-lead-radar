from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(slots=True)
class Classification:
    label: str
    level: str
    score: int
    reason: str
    suggested_reply: str


INTENT_RULES: dict[str, list[tuple[str, int]]] = {
    "同行意向": [
        ("怎么报名", 42), ("如何报名", 42), ("还有位置", 40), ("一起去", 36),
        ("可以一起", 36), ("求组队", 36), ("约伴", 34), ("同行", 30),
        ("带我一个", 34), ("算我一个", 34), ("我也想去", 28), ("准备去", 28),
        ("计划去", 26), ("想去南极", 28), ("有群吗", 28),
        ("join", 30), ("go together", 36), ("travel partner", 36),
        ("go to antarctica", 30), ("antarctica trip", 24),
    ],
    "预算价格": [
        ("多少钱", 38), ("费用", 30), ("预算", 32), ("价格", 28),
        ("船票", 26), ("贵不贵", 26), ("需要多少", 28),
        ("how much", 38), ("cost", 30), ("price", 28), ("budget", 32),
    ],
    "时间船期": [
        ("什么时候", 32), ("几月份", 30), ("时间", 20), ("船期", 34),
        ("2027", 22), ("多久", 22), ("哪天", 24),
        ("when", 30), ("departure", 26), ("schedule", 28),
    ],
    "路线攻略": [
        ("路线", 28), ("乌斯怀亚", 25), ("德雷克", 25), ("怎么去", 30),
        ("攻略", 24), ("签证", 28), ("从哪里出发", 30),
        ("route", 28), ("ushuaia", 25), ("drake passage", 25), ("visa", 28),
    ],
    "安全准备": [
        ("安全吗", 34), ("保险", 28), ("晕船", 30), ("身体", 22),
        ("体能", 24), ("装备", 24), ("风险", 26), ("医疗", 25),
        ("safe", 30), ("insurance", 28), ("seasick", 30), ("risk", 26),
    ],
    "摄影共创": [
        ("摄影", 26), ("拍摄", 24), ("纪录片", 30), ("航拍", 26),
        ("剪辑", 24), ("共创", 32), ("摄像", 24),
        ("photographer", 28), ("documentary", 30), ("filmmaker", 28), ("collaborate", 30),
    ],
    "品牌合作": [
        ("合作", 30), ("赞助", 34), ("品牌", 26), ("媒体采访", 34),
        ("商务", 28), ("资源置换", 32),
        ("sponsor", 34), ("partnership", 30), ("brand collaboration", 34),
    ],
    "普通关注": [
        ("好想去", 18), ("一定要去", 20), ("太美了", 8), ("真美", 8),
        ("震撼", 8), ("企鹅", 6), ("关注了", 16),
    ],
}

EXCLUDE_PATTERNS = [
    r"加微[信vx]", r"兼职", r"刷单", r"代购", r"博彩", r"贷款", r"私聊.*赚钱",
]

REPLIES = {
    "同行意向": "看到你也在计划去南极。我们正在公开筹备“2027南极陆行与影像记录项目”，目前是同行意向登记阶段，路线、预算和装备都会持续更新，可以进入我的主页查看置顶介绍。",
    "预算价格": "南极费用主要由探险船票、国际交通、保险和装备组成。我们正在整理2027年的完整预算框架，主页置顶内容会逐项公开，建议先了解预算再决定是否进入同行候选名单。",
    "时间船期": "我们正在根据2027年船期规划出发窗口，路线会经过南美集结、乌斯怀亚和德雷克海峡。确定后的时间线会在主页筹备日志更新，欢迎先关注进度。",
    "路线攻略": "我们正在做从亚洲出发、南美集结、乌斯怀亚启航到南极半岛的完整路线研究。主页会持续公开签证、交通和船期信息，可以先看置顶项目介绍。",
    "安全准备": "南极项目需要认真考虑天气、德雷克海峡、保险和医疗条件。我们不会承诺绝对安全，正在做完整的装备和风险准备，主页会持续公开筹备过程。",
    "摄影共创": "我们的2027南极项目也在招募摄影、视频和纪录片共创者。如果你关注极地影像，可以进入主页查看项目介绍，后续会开放内容共创申请。",
    "品牌合作": "感谢关注。Antarctica 2027正在筹备品牌与媒体合作，覆盖装备测试、出发前记录和南极纪录片内容。可以进入主页查看项目介绍并通过合作入口联系。",
    "普通关注": "我们正在用一年时间记录2027南极项目的完整筹备过程，路线、预算、装备和幕后都会公开，欢迎进入主页一起见证。",
    "无关": "",
}

REPLIES_EN = {
    "同行意向": "We are documenting an Antarctica 2027 overland and expedition project. The plan is currently open for travel-interest registration, with route, budget and preparation updates available from our profile.",
    "预算价格": "The main costs are the expedition voyage, international transport, insurance and polar gear. We are preparing a transparent Antarctica 2027 budget breakdown and will publish it through our profile.",
    "时间船期": "We are aligning the project with the 2027 expedition schedule, including South America, Ushuaia and the Drake Passage. The confirmed timeline will be published in our preparation log.",
    "路线攻略": "Our route research covers departure from Asia, assembly in South America, Ushuaia and the Antarctic Peninsula. Visa, transport and voyage notes will be shared through our project profile.",
    "安全准备": "Antarctica involves real weather, medical, insurance and Drake Passage risks. We are documenting the preparation process and will only work through qualified travel partners and operators.",
    "摄影共创": "The Antarctica 2027 project is also exploring photography, video and documentary collaboration. Please see the project introduction on our profile for future creator applications.",
    "品牌合作": "Antarctica 2027 is open to relevant brand and media partnerships across gear testing, preparation stories and documentary content. Project details are available through our profile.",
    "普通关注": "We are documenting the full Antarctica 2027 preparation journey, including route, budget, gear and behind-the-scenes work. You are welcome to follow the project through our profile.",
    "无关": "",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _reply_for(text: str, label: str) -> str:
    latin = len(re.findall(r"[A-Za-z]", text))
    han = len(re.findall(r"[\u4e00-\u9fff]", text))
    return REPLIES_EN[label] if latin > han * 2 and latin >= 8 else REPLIES[label]


def classify_rule_based(text: str) -> Classification:
    normalized = _normalize(text)
    if not normalized:
        return Classification("无关", "排除", 0, "评论内容为空", "")

    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return Classification("无关", "排除", 0, "疑似广告或无关推广", "")

    category_scores: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for category, rules in INTENT_RULES.items():
        total = 0
        category_hits: list[str] = []
        for phrase, weight in rules:
            if phrase.lower() in normalized:
                total += weight
                category_hits.append(phrase)
        if total:
            category_scores[category] = min(total, 100)
            hits[category] = category_hits

    if not category_scores:
        return Classification("无关", "排除", 5, "未发现南极旅行相关意向", "")

    label = max(category_scores, key=category_scores.get)
    score = category_scores[label]

    # Cross-category signals increase confidence without changing the leading intent.
    active_categories = len(category_scores)
    if active_categories > 1:
        score = min(100, score + min(18, (active_categories - 1) * 6))
    if "南极" in normalized:
        score = min(100, score + 8)
    if any(mark in text for mark in ("？", "?")):
        score = min(100, score + 5)

    if score >= 70:
        level = "A级"
    elif score >= 40:
        level = "B级"
    else:
        level = "C级"

    reason_parts = [f"识别到{label}关键词：{'、'.join(hits[label])}"]
    if active_categories > 1:
        reason_parts.append(f"同时包含{active_categories}类相关信号")
    return Classification(label, level, score, "；".join(reason_parts), _reply_for(text, label))


def classify_with_ollama(
    text: str,
    base_url: str = "http://127.0.0.1:11434",
    model: str = "qwen2.5:3b",
    timeout: int = 25,
) -> Classification:
    """Use a local Ollama model; fall back to deterministic rules on any error."""
    fallback = classify_rule_based(text)
    prompt = f"""你是南极旅行项目的评论意向分类器。只分析评论文本，不推断年龄、健康、收入等敏感信息。
可选类别：同行意向、预算价格、时间船期、路线攻略、安全准备、摄影共创、品牌合作、普通关注、无关。
输出严格JSON：{{"label":"", "score":0, "reason":""}}。score范围0-100。
评论：{text}
"""
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": "json"}).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            outer = json.loads(response.read().decode("utf-8"))
        parsed = json.loads(outer.get("response", "{}"))
        label = str(parsed.get("label", fallback.label))
        if label not in REPLIES:
            return fallback
        score = max(0, min(100, int(parsed.get("score", fallback.score))))
        level = "A级" if score >= 70 else "B级" if score >= 40 else "C级" if score > 0 else "排除"
        return Classification(label, level, score, str(parsed.get("reason", fallback.reason)), _reply_for(text, label))
    except (OSError, ValueError, KeyError, urllib.error.URLError, json.JSONDecodeError):
        return fallback
