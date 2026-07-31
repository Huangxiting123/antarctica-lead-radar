# OmniMedia Intelligence Radar｜全域媒介情报雷达

Windows 本地桌面软件，用于把多个自媒体平台的公开内容、授权账号评论与合规导出数据统一整理为可审核的商机线索。项目名称、主题关键词、高意向词、排除词和回复引导均可更换，不再局限于南极旅行。

## 核心能力

- 本地 SQLite 数据库，自动迁移 Antarctica Lead Radar v0.1 的旧数据。
- 支持任意项目、品牌、产品、活动、课程、旅行或服务主题。
- 离线规则 AI 或本机 Ollama：A级、B级、C级、排除。
- 平台连接中心统一显示接入方式、能力范围、地区方式和官方说明。
- YouTube：官方关键词视频搜索、语言/地区相关性、公开评论。
- 抖音：已授权账号视频评论、人工确认后的单条官方回复。
- X / Twitter：官方近期帖文与回复搜索，支持语言和精确地理标签国家。
- Reddit：官方 OAuth 搜索社区帖子并读取公开评论。
- Facebook：已授权 Page 帖子评论。
- Instagram：已授权专业账号自有媒体评论。
- TikTok：仅限通过资格审核的 Research API 项目，支持注册地区和日期范围。
- 快手、西瓜视频、今日头条、百家号、小红书、Bilibili、微信视频号：开放平台授权或标准 CSV 导入入口。
- CSV / Excel 导出、来源打开、回复复制、处理状态和本地审计。
- 凭证只保存在当前进程内存，不写入数据库。

## 为什么不同平台的能力不一样

多数平台没有向普通商业应用开放“按关键词搜索全站视频并读取全部评论”的接口。软件因此把接入分为：

1. 官方公开搜索：如 YouTube、X、Reddit，受配额和套餐约束。
2. 已授权账号：如抖音、Facebook Page、Instagram 专业账号。
3. 受限研究接口：如 TikTok Research API，仅面向符合资格的非营利研究。
4. 合规导入：创作者后台、平台授权数据或正式数据服务导出的 CSV。

软件不会调用逆向接口、接管 Cookie、破解签名、绕过验证码或规避平台风控。

## Windows 使用

### 便携 EXE

下载 `OmniMediaIntelligenceRadar.exe` 后直接运行。数据库位于：

```text
%LOCALAPPDATA%\OmniMediaIntelligenceRadar\lead_radar.db
```

首次运行会尝试从旧目录复制 v0.1 数据，旧数据库不会被删除。

### 源码运行

系统要求 Windows 10/11、Python 3.10+。双击 `run_windows.bat`，或执行：

```bash
python app.py
```

### 自行构建

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

输出：

```text
dist\OmniMediaIntelligenceRadar.exe
```

## 首次配置流程

1. 打开“项目与AI设置”。
2. 填写项目/品牌名称、简介、主题词、高意向词、排除词和回复结尾。
3. 打开“平台连接中心”。
4. 选择平台，查看官方接入要求。
5. 有官方凭证的平台选择“配置/开始采集”；其他平台使用“导入所选平台CSV”。
6. 按 A/B 级审核线索，人工检查建议回复。
7. 复制回复到平台或仅在明确支持的已授权账号接口中发布。

## CSV 格式

最少需要“评论内容”列，推荐表头：

```csv
平台,用户名称,平台用户标识,评论内容,评论时间,视频标题,视频链接,评论ID
```

也支持：

```text
platform,user_name,user_id,content,comment_time,video_title,video_url,comment_id
```

## 地区筛选说明

- YouTube 的 `regionCode` 表示可观看区域与结果相关性，不代表评论者所在地。
- X 的 `place_country` 只匹配带地理标签的帖子，覆盖率有限。
- TikTok Research API 的 `region_code` 表示创作者注册地区。
- Reddit 没有可靠的国家字段，可用 subreddit、语言与地区关键词近似筛选。
- Facebook/Instagram 授权账号模式按所连接账号的目标市场管理，而不是全站地区搜索。

## 官方资料

- YouTube Search API: <https://developers.google.com/youtube/v3/docs/search/list>
- 抖音视频评论管理: <https://open.douyin.com/platform/resource/docs/ability/interaction-management/video-comment-management-solution>
- X Search API: <https://docs.x.com/x-api/posts/search/introduction>
- Reddit API: <https://www.reddit.com/dev/api/>
- Facebook Pages API: <https://developers.facebook.com/documentation/pages-api>
- Instagram Platform: <https://developers.facebook.com/documentation/instagram-platform>
- TikTok Research API: <https://developers.tiktok.com/doc/research-api-get-started>
- 快手开放平台: <https://open.kuaishou.com/>
- Bilibili 开放平台: <https://openhome.bilibili.com/doc>

## 安全边界

- 不采集私信、通讯录、手机号、微信号或其他非公开数据。
- 不通过昵称反查真实身份。
- 不自动群发营销评论。
- 不绕过平台权限、限流、登录保护或验证码。
- 对拒绝联系的用户应立即标记忽略并停止跟进。
- 实际可用能力取决于平台审核、应用权限、配额、套餐和最新开发者条款。

## 测试

```bash
python -m unittest discover -s tests -v
python -m compileall app.py src tests
```
