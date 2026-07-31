from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformSpec:
    key: str
    name: str
    connection: str
    capabilities: str
    region_mode: str
    status: str
    note: str
    docs_url: str


PLATFORMS: tuple[PlatformSpec, ...] = (
    PlatformSpec("youtube", "YouTube", "官方 API Key", "关键词搜索、公开视频评论", "国家/地区 + 语言", "可直接配置", "使用 YouTube Data API；回复功能需要另行 OAuth 授权。", "https://developers.google.com/youtube/v3/docs/search/list"),
    PlatformSpec("douyin", "抖音", "官方 OAuth", "授权账号视频评论、人工确认回复", "中国大陆", "可直接配置", "仅处理已授权账号及开放平台允许访问的视频。", "https://open.douyin.com/platform/resource/docs/ability/interaction-management/video-comment-management-solution"),
    PlatformSpec("x", "X / Twitter", "官方 Bearer Token", "近期公开帖文/回复关键词搜索", "国家/地区 + 语言", "可直接配置", "地区筛选依赖帖文地理标签，结果可能较少；历史范围受套餐限制。", "https://docs.x.com/x-api/posts/search/introduction"),
    PlatformSpec("reddit", "Reddit", "官方 OAuth", "社区帖子搜索、公开评论", "社区/语言近似", "可直接配置", "Reddit 没有可靠的国家过滤；可用 subreddit、语言和地区词缩小范围。", "https://www.reddit.com/dev/api/"),
    PlatformSpec("facebook", "Facebook", "Meta OAuth / Page Token", "自有或已授权 Page 帖子评论", "主页所属市场", "可直接配置", "普通应用不能任意抓取全站用户评论；需要 Page 权限和审核。", "https://developers.facebook.com/documentation/pages-api"),
    PlatformSpec("instagram", "Instagram", "Meta OAuth", "专业账号自有媒体评论", "账号受众市场", "可直接配置", "仅适用于已授权的 Instagram 专业账号媒体。", "https://developers.facebook.com/documentation/instagram-platform"),
    PlatformSpec("tiktok", "TikTok", "Research API Token", "批准范围内的视频关键词与评论", "国家/地区", "研究权限配置", "Research API 只向符合资格并获批的研究项目开放，不适用于一般商业获客。", "https://developers.tiktok.com/doc/research-api-get-started"),
    PlatformSpec("kuaishou", "快手", "开放平台授权 / 导入", "授权账号作品数据、文件导入", "中国大陆", "合规导入", "开放能力以控制台已审批权限为准；不调用未公开接口。", "https://open.kuaishou.com/"),
    PlatformSpec("xigua", "西瓜视频", "授权数据 / 导入", "作品与评论文件导入", "中国大陆", "合规导入", "公开开发文档主要提供播放/嵌入能力，评论监听需商务或平台授权。", "https://developers.ixigua.com/"),
    PlatformSpec("toutiao", "今日头条", "授权数据 / 导入", "文章、视频、评论文件导入", "中国大陆", "合规导入", "按开放平台或创作者后台实际可导出数据接入。", "https://open.toutiao.com/"),
    PlatformSpec("baijiahao", "百家号", "授权数据 / 导入", "内容与互动数据导入", "中国大陆", "合规导入", "仅使用账号后台导出或正式开放能力。", "https://baijiahao.baidu.com/"),
    PlatformSpec("xiaohongshu", "小红书", "专业号/商业授权 / 导入", "笔记与评论文件导入", "中国大陆", "合规导入", "不使用逆向签名、Cookie 接管或验证码绕过。", "https://open.xiaohongshu.com/"),
    PlatformSpec("bilibili", "Bilibili", "开放平台授权 / 导入", "授权账号数据、评论文件导入", "中国大陆", "合规导入", "使用开放平台批准能力；不调用所谓“野生 API”批量采集。", "https://openhome.bilibili.com/doc"),
    PlatformSpec("wechat_channels", "微信视频号", "账号后台 / 导入", "自有账号互动数据导入", "中国大陆", "合规导入", "当前不接入逆向协议；微信小店接口不等于全站视频号评论接口。", "https://channels.weixin.qq.com/"),
)


PLATFORM_BY_KEY = {item.key: item for item in PLATFORMS}


REGIONS: tuple[tuple[str, str], ...] = (
    ("不限地区", ""), ("中国大陆", "CN"), ("中国香港", "HK"), ("中国台湾", "TW"),
    ("日本", "JP"), ("韩国", "KR"), ("新加坡", "SG"), ("泰国", "TH"),
    ("印度尼西亚", "ID"), ("澳大利亚", "AU"), ("新西兰", "NZ"),
    ("美国", "US"), ("加拿大", "CA"), ("墨西哥", "MX"),
    ("英国", "GB"), ("法国", "FR"), ("德国", "DE"), ("西班牙", "ES"),
    ("意大利", "IT"), ("巴西", "BR"), ("阿根廷", "AR"), ("智利", "CL"),
    ("南非", "ZA"), ("阿联酋", "AE"), ("沙特阿拉伯", "SA"), ("印度", "IN"),
)


LANGUAGES: tuple[tuple[str, str], ...] = (
    ("自动/不限", ""), ("简体中文", "zh-Hans"), ("繁体中文", "zh-Hant"),
    ("英语", "en"), ("日语", "ja"), ("韩语", "ko"), ("西班牙语", "es"),
    ("葡萄牙语", "pt"), ("法语", "fr"), ("德语", "de"), ("俄语", "ru"),
    ("阿拉伯语", "ar"), ("印尼语", "id"), ("泰语", "th"),
)


def option_code(label: str, options: tuple[tuple[str, str], ...]) -> str:
    return dict(options).get(label, "")
