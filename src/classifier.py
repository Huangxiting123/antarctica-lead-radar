from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Classification:
    label: str
    level: str
    score: int
    reason: str
    suggested_reply: str


DEFAULT_PROFILE: dict[str, str] = {
    "project_name": "2027 南极旅行项目",
    "project_intro": "我们正在公开筹备项目，相关计划、费用和进展会持续发布。",
    "project_keywords": "南极,Antarctica,乌斯怀亚,德雷克",
    "high_intent_keywords": "怎么报名,如何参加,多少钱,价格,费用,一起去,同行,合作,赞助,how much,how to join,interested,price,cost",
    "exclude_keywords": "兼职,刷单,博彩,贷款,私聊赚钱",
    "reply_signature": "详情可进入主页查看项目介绍。",
}


INTENT_RULES: dict[str, list[tuple[str, int]]] = {
    "报名预约": [
        ("怎么报名", 45), ("如何报名", 45), ("如何参加", 42), ("怎么参加", 42),
        ("预约", 34), ("加入", 30), ("一起去", 36), ("同行", 30), ("带我一个", 34),
        ("sign up", 42), ("how to join", 45), ("can i join", 42), ("register", 34),
        ("want to go", 28), ("interested", 25), ("参加したい", 36), ("참가하고", 36),
        ("quiero participar", 36), ("como participar", 38),
    ],
    "价格预算": [
        ("多少钱", 42), ("费用", 30), ("预算", 32), ("价格", 30), ("报价", 36),
        ("贵不贵", 28), ("how much", 42), ("cost", 30), ("price", 30), ("budget", 32),
        ("cuánto cuesta", 42), ("quanto custa", 42), ("費用はいくら", 42), ("비용", 30),
    ],
    "购买咨询": [
        ("怎么买", 40), ("怎么购买", 40), ("哪里买", 36), ("下单", 32), ("链接", 18),
        ("有货吗", 34), ("购买", 24), ("where to buy", 38), ("how to buy", 40),
        ("order", 25), ("available", 22),
    ],
    "时间安排": [
        ("什么时候", 34), ("几月份", 32), ("哪天", 28), ("多久", 24), ("档期", 30),
        ("when", 32), ("schedule", 30), ("date", 24), ("how long", 26),
    ],
    "功能需求": [
        ("怎么用", 34), ("如何使用", 34), ("支持", 20), ("功能", 22), ("教程", 24),
        ("how to use", 34), ("does it support", 32), ("feature", 22), ("tutorial", 24),
    ],
    "问题反馈": [
        ("不能用", 38), ("打不开", 38), ("失败", 28), ("问题", 18), ("退款", 40),
        ("投诉", 40), ("坏了", 36), ("not working", 38), ("refund", 40),
        ("issue", 24), ("problem", 24),
    ],
    "安全与风险": [
        ("安全吗", 38), ("安全", 22), ("保险", 28), ("风险", 30), ("身体", 18),
        ("医疗", 25), ("晕船", 28), ("safe", 30), ("safety", 30),
        ("insurance", 28), ("risk", 28),
    ],
    "内容共创": [
        ("摄影", 24), ("拍摄", 24), ("纪录片", 28), ("剪辑", 22), ("共创", 34),
        ("创作者", 22), ("photographer", 28), ("documentary", 28), ("filmmaker", 28),
        ("creator", 22), ("collaborate", 30),
    ],
    "品牌合作": [
        ("合作", 32), ("赞助", 38), ("品牌", 26), ("媒体采访", 36), ("商务", 30),
        ("资源置换", 34), ("sponsor", 38), ("partnership", 34),
        ("brand collaboration", 38), ("business inquiry", 34),
    ],
    "普通关注": [
        ("想了解", 18), ("感兴趣", 20), ("关注了", 18), ("期待", 14), ("收藏", 12),
        ("太好了", 8), ("interested", 18), ("following", 14), ("looks great", 8),
    ],
}


SPAM_PATTERNS = [r"加微[信vx]", r"兼职", r"刷单", r"博彩", r"贷款", r"私聊.*赚钱", r"代充", r"秒到账"]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _terms(value: str) -> list[str]:
    return [item.strip().lower() for item in re.split(r"[,，;；\n|]", value or "") if item.strip()]


def _profile(profile: dict[str, Any] | None) -> dict[str, str]:
    merged = dict(DEFAULT_PROFILE)
    if profile:
        merged.update({key: str(value or "") for key, value in profile.items()})
    return merged


def _is_english(text: str) -> bool:
    latin = len(re.findall(r"[A-Za-z]", text))
    han = len(re.findall(r"[\u4e00-\u9fff]", text))
    return latin >= 8 and latin > han * 2


def _build_reply(text: str, label: str, profile: dict[str, str]) -> str:
    project = profile["project_name"] or "当前项目"
    intro = profile["project_intro"].strip()
    signature = profile["reply_signature"].strip()
    if _is_english(text):
        lead = {
            "报名预约": f"Thanks for your interest in {project}. We are currently collecting qualified enquiries and participation interest.",
            "价格预算": f"Pricing and budget details for {project} depend on the selected plan. We are preparing a clear cost breakdown.",
            "购买咨询": f"Thanks for asking about {project}. Please check the official project information before making a purchase decision.",
            "时间安排": f"The latest schedule and availability for {project} will be published through our official project updates.",
            "功能需求": f"Thanks for your question about {project}. We will confirm the applicable features and instructions before advising you.",
            "问题反馈": f"Thank you for reporting this issue with {project}. Please use the official support channel so the details can be checked safely.",
            "安全与风险": f"Safety, insurance and risk questions about {project} require verified information. We will not make absolute safety promises.",
            "内容共创": f"{project} is open to relevant creator and media collaboration after review.",
            "品牌合作": f"{project} welcomes relevant brand and media partnership enquiries after review.",
            "普通关注": f"Thank you for following {project}. We will continue publishing verified updates.",
        }[label]
        return lead + (" Please visit our profile for the official introduction." if signature else "")
    lead = {
        "报名预约": f"看到你对“{project}”有参与意向。我们正在收集真实需求并进行人工审核，",
        "价格预算": f"“{project}”的价格与预算会根据具体方案确定，我们正在整理透明的费用说明，",
        "购买咨询": f"感谢关注“{project}”。购买或报名之前建议先核对官方项目说明，",
        "时间安排": f"“{project}”的时间、档期和名额会以正式更新为准，",
        "功能需求": f"感谢咨询“{project}”的使用方式和功能，我们会根据实际场景确认后再答复，",
        "问题反馈": f"收到你关于“{project}”的问题反馈，建议通过官方支持渠道提供必要信息，",
        "安全与风险": f"“{project}”涉及的安全、保险和风险问题需要依据正式资料判断，我们不会作绝对安全承诺，",
        "内容共创": f"“{project}”正在接收相关创作者、摄影与内容共创意向，",
        "品牌合作": f"“{project}”可接收匹配的品牌、媒体与商务合作意向，",
        "普通关注": f"感谢关注“{project}”，我们会持续发布经过确认的项目进展，",
    }[label]
    detail = intro if intro else "相关信息会通过官方渠道持续更新。"
    return f"{lead}{detail}{signature}"


def classify_rule_based(text: str, profile: dict[str, Any] | None = None) -> Classification:
    config = _profile(profile)
    normalized = _normalize(text)
    if not normalized:
        return Classification("无关", "排除", 0, "内容为空", "")

    exclude_terms = _terms(config["exclude_keywords"])
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return Classification("无关", "排除", 0, "疑似广告、诈骗或无关推广", "")
    if any(term in normalized for term in exclude_terms):
        return Classification("无关", "排除", 0, "命中项目排除词", "")

    category_scores: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for category, rules in INTENT_RULES.items():
        matched = [(phrase, weight) for phrase, weight in rules if phrase.lower() in normalized]
        if matched:
            category_scores[category] = min(100, sum(weight for _, weight in matched))
            hits[category] = [phrase for phrase, _ in matched]

    project_hits = [term for term in _terms(config["project_keywords"]) if term in normalized]
    high_hits = [term for term in _terms(config["high_intent_keywords"]) if term in normalized]
    if not category_scores and project_hits:
        category_scores["普通关注"] = 20
        hits["普通关注"] = project_hits
    if not category_scores:
        return Classification("无关", "排除", 5, "未发现与当前项目相关的明确意向", "")

    label = max(category_scores, key=category_scores.get)
    score = category_scores[label]
    if project_hits:
        score = min(100, score + 12)
    if high_hits:
        score = min(100, score + 18)
    if len(category_scores) > 1:
        score = min(100, score + min(18, (len(category_scores) - 1) * 6))
    if any(mark in text for mark in ("？", "?")):
        score = min(100, score + 5)

    level = "A级" if score >= 70 else "B级" if score >= 40 else "C级"
    reason = f"识别到{label}信号：{'、'.join(hits[label])}"
    if project_hits:
        reason += f"；命中项目词：{'、'.join(project_hits[:5])}"
    return Classification(label, level, score, reason, _build_reply(text, label, config))


def classify_with_ollama(text: str, base_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:3b", timeout: int = 25, profile: dict[str, Any] | None = None) -> Classification:
    config = _profile(profile)
    fallback = classify_rule_based(text, config)
    prompt = f"""你是跨平台公开内容的商机意向分类器。只依据当前文本判断，不推断年龄、健康、收入、住址等敏感信息。
当前项目：{config['project_name']}
项目关键词：{config['project_keywords']}
可选类别：报名预约、价格预算、购买咨询、时间安排、功能需求、问题反馈、安全与风险、内容共创、品牌合作、普通关注、无关。
输出严格JSON：{{"label":"", "score":0, "reason":""}}。score范围0-100。
文本：{text}
"""
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": "json"}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(base_url.rstrip("/") + "/api/generate", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            outer = json.loads(response.read().decode("utf-8"))
        parsed = json.loads(outer.get("response", "{}"))
        label = str(parsed.get("label", fallback.label))
        if label not in INTENT_RULES:
            return fallback
        score = max(0, min(100, int(parsed.get("score", fallback.score))))
        level = "A级" if score >= 70 else "B级" if score >= 40 else "C级" if score > 0 else "排除"
        return Classification(label, level, score, str(parsed.get("reason", fallback.reason)), _build_reply(text, label, config))
    except (OSError, ValueError, KeyError, urllib.error.URLError, json.JSONDecodeError):
        return fallback
