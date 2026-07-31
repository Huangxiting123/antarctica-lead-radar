# Antarctica Lead Radar｜南极意向雷达

Windows 本地桌面软件，用于收集**官方接口授权或手工导入**的公开评论，识别与 2027 南极同行、预算、路线、安全、摄影和品牌合作有关的意向，并在人工审核后生成或发布回复。

## 已完成能力

- 本地 SQLite 数据库，评论不会默认上传云端。
- 中文 CSV 导入，兼容 UTF-8 与 GB18030。
- 规则式 AI 意向识别：A级、B级、C级、排除。
- 可选连接本机 Ollama 模型，失败时自动退回离线规则。
- 评论线索表：用户名称、平台用户标识、评论、时间、来源、意向、分数、建议回复、状态。
- CSV 和 Excel `.xlsx` 导出，包含筛选、冻结表头和防公式注入处理。
- 抖音开放平台授权评论采集和单条回复接口。
- YouTube Data API 关键词视频搜索及评论采集。
- 人工审核工作台：复制回复、打开原视频、标记忽略、确认后发布。
- API 密钥只保存在本次软件运行内存中，不写入数据库。

## 不包含的能力

- 不破解平台登录、验证码、Cookie 或签名算法。
- 不抓取私人手机号、微信或非公开资料。
- 不自动群发第三方视频营销评论。
- 不绕过平台限流或风控。
- 不把“公开昵称”反查成更多个人身份信息。

## Windows 直接运行源码

系统要求：Windows 10/11，Python 3.10 或更高版本。

1. 解压源码包。
2. 双击 `run_windows.bat`。
3. 首次启动后，本地数据库创建在：
   `%LOCALAPPDATA%\AntarcticaLeadRadar\lead_radar.db`
4. 点击“导入CSV”，可以使用 `sample/comments_demo.csv` 验证完整流程。

本程序运行不需要安装第三方 Python 包。

## 构建 Windows EXE

在 PowerShell 中执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

完成后得到：

```text
dist\AntarcticaLeadRadar.exe
```

## 抖音官方接口准备

需要在抖音开放平台创建应用并申请：

- `video.list`：授权账号视频列表。
- `video.comment`：评论列表和回复评论。

软件中的抖音采集只适用于授权账号及接口允许访问的视频。输入：

- Access Token
- 授权账号 Open ID
- 视频 Item ID
- 可选的视频标题和链接

密钥只在本次运行中保存在内存里，退出软件后清除。正式部署前仍建议定期轮换令牌。

官方说明：<https://open.douyin.com/platform/resource/docs/ability/interaction-management/video-comment-management-solution>

## YouTube 官方接口准备

1. 在 Google Cloud Console 创建项目。
2. 启用 YouTube Data API v3。
3. 创建 API Key，并设置 API 限制。
4. 在软件中输入 API Key、关键词、视频数和每个视频的评论上限。

第一版使用公开搜索和公开评论读取接口，不自动发布 YouTube 回复。

官方说明：

- <https://developers.google.com/youtube/v3/docs/search/list>
- <https://developers.google.com/youtube/v3/docs/commentThreads/list>

## CSV 导入格式

最少需要“评论内容”列。推荐表头：

```csv
平台,用户名称,平台用户标识,评论内容,评论时间,视频标题,视频链接,评论ID
```

也支持部分英文表头：`platform,user_name,user_id,content,comment_time,video_title,video_url,comment_id`。

## AI模式

### 离线规则引擎

默认模式，无需联网。按照同行、价格、时间、路线、安全、摄影和合作关键词打分，适合第一轮筛选。

### 本机 Ollama

1. 安装 Ollama。
2. 在本机准备中文模型，例如 `qwen2.5:3b`。
3. 软件设置中选择“本机Ollama模型”。
4. 默认地址：`http://127.0.0.1:11434`。

评论只发送到本机 Ollama 服务；本机模型不可用时自动退回规则引擎。

## 完整业务流程

1. 运营人员建立南极关键词库。
2. 使用官方API搜索或手工添加视频来源。
3. 采集平台允许访问的评论。
4. 根据平台评论ID去重并写入本地数据库。
5. AI识别意向类型、等级、分数和判断原因。
6. 运营人员按A级/B级筛选。
7. 查看原评论和来源视频。
8. 人工修改建议回复。
9. 自有授权抖音视频可通过官方接口单条回复；其他来源复制后人工处理。
10. 导出Excel/CSV并与报名表或CRM核对。
11. 用户拒绝营销后标记忽略，不再跟进。

## 测试

```bash
python -m unittest discover -s tests -v
python -m compileall app.py src tests
```

## 后续版本路线

- 抖音 OAuth 浏览器授权向导。
- 授权账号视频选择器，不再手动输入 Item ID。
- YouTube OAuth 与人工确认回复。
- B站、头条、西瓜的已授权账号连接器。
- 南极网站报名数据匹配与CRM阶段管理。
- 回复模板审批、团队账号和操作审计。
- 数据保存期限与一键删除策略。

## 重要说明

本软件是本地内容运营辅助工具，不是无授权爬虫或群发工具。平台接口能力会变化，实际可用范围以平台审核结果、开放权限和最新开发者条款为准。
