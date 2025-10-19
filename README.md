# TikHub 自动签到脚本

自动完成 TikHub 每日签到，支持本地运行和 GitHub Actions 云端运行，支持 Telegram 通知。

## ✨ 功能特点

- ✅ 自动签到，无需手动操作
- ✅ 支持账号密码登录和 Cookie 登录
- ✅ 自动处理 reCAPTCHA 验证
- ✅ 自动保存和管理 Cookie
- ✅ 签到记录统计
- ✅ Telegram 消息通知
- ✅ GitHub Actions 云端自动运行
- ✅ 美化的通知消息（含每日一言）

## 📦 安装依赖

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

## 🚀 使用方法

### 方式一：本地运行

#### 1. 配置账号信息

编辑 `tikhub_signin_playwright.py` 文件，或设置环境变量：

**使用账号密码（推荐）：**
```bash
export TIKHUB_EMAIL="your_email@example.com"
export TIKHUB_PASSWORD="your_password"
```

**使用 Cookie：**
```bash
export TIKHUB_COOKIE="your_cookie_here"
```

**配置 Telegram 通知（可选）：**
```bash
export TG_BOT_TOKEN="your_bot_token"
export TG_CHAT_ID="your_chat_id"
```

#### 2. 运行脚本

```bash
python tikhub_signin_playwright.py
```

### 方式二：GitHub Actions 自动运行（推荐）

#### 1. Fork 本仓库

点击右上角的 Fork 按钮，将本仓库 Fork 到你的账号下。

#### 2. 配置 GitHub Secrets

进入你 Fork 的仓库，依次点击：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

添加以下 Secrets：

| Secret 名称 | 说明 | 是否必需 |
|------------|------|---------|
| `TIKHUB_EMAIL` | TikHub 账号邮箱 | ✅ 二选一 |
| `TIKHUB_PASSWORD` | TikHub 账号密码 | ✅ 配合邮箱 |
| `TIKHUB_COOKIE` | TikHub Cookie | ✅ 二选一 |
| `TG_BOT_TOKEN` | Telegram Bot Token | ⭐ 可选 |
| `TG_CHAT_ID` | Telegram Chat ID | ⭐ 可选 |

**推荐使用账号密码方式**，因为 Cookie 会过期，而账号密码可以自动重新登录。

#### 3. 启用 Actions

1. 进入 `Actions` 标签页
2. 如果看到提示，点击 `I understand my workflows, go ahead and enable them`
3. 在左侧找到 `TikHub 自动签到` 工作流
4. 点击 `Enable workflow`

#### 4. 手动测试

1. 点击 `Run workflow` 按钮
2. 选择 `main` 分支
3. 点击绿色的 `Run workflow` 按钮
4. 等待执行完成，查看日志

#### 5. 自动运行

配置完成后，脚本会在每天北京时间 8:00 自动运行。

## 📱 配置 Telegram 通知

### 1. 创建 Telegram Bot

1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 命令
3. 按提示设置 Bot 名称
4. 获得 Bot Token（类似 `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）

### 2. 获取 Chat ID

1. 在 Telegram 中搜索 `@userinfobot`
2. 发送任意消息
3. Bot 会返回你的 Chat ID（纯数字）

### 3. 添加到 GitHub Secrets

将上述获得的 `Bot Token` 和 `Chat ID` 添加到 GitHub Secrets 中。

### 4. 通知效果预览

```
✨ TikHub每日签到 ✨

📅 日期: 2025年01月19日 (星期日)
🕒 时间: 08:05:32
👤 账号: your_email@example.com
✅ 状态: 签到成功
🔑 登录方式: 账号密码
✅ 签到方式: Cookie签到
💎 本次获得: +10 积分

📊 签到统计:
  · 总计已签到: 15 天
  · 01月已签到: 5 天
  · 今日首次签到 🆕

🚀 打卡成功！向着梦想飞奔吧~

📝 每日一言: 不要等待，时机永远不会恰到好处。 —— 拿破仑·希尔
```

## 📊 签到记录

脚本会自动记录签到信息，保存在以下文件中：

- `tikhub_checkin_record.json` - 签到记录（总天数、每月统计）
- `tikhub_cookies.json` - Cookie 缓存（自动管理）

## 🔧 自定义配置

### 修改运行时间

编辑 `.github/workflows/tikhub_checkin.yml` 文件中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 0:00，即北京时间 8:00
```

**常用时间：**
- `0 0 * * *` - 北京时间 08:00
- `0 1 * * *` - 北京时间 09:00
- `0 23 * * *` - 北京时间 07:00

### 无头模式 vs 有头模式

脚本会自动检测运行环境：
- **GitHub Actions**：自动使用无头模式
- **本地运行**：默认有头模式（可以看到浏览器）

如需本地无头模式，修改代码：
```python
headless=True  # 改为 True
```

## 📝 Cookie 获取方法

如果选择使用 Cookie 方式：

1. 在浏览器中登录 TikHub
2. 打开开发者工具（F12）
3. 切换到 "Network"（网络）标签
4. 刷新页面
5. 找到任意请求，查看 "Request Headers"
6. 复制 `Cookie` 字段的完整值

## ❓ 常见问题

### Q: 签到失败怎么办？

**A:** 检查以下几点：
1. Cookie 是否过期（使用账号密码方式更稳定）
2. 账号密码是否正确
3. 查看 Actions 日志，了解具体错误信息
4. 检查 Secrets 是否正确配置

### Q: Cookie 会过期吗？

**A:** 会的。建议使用账号密码方式，脚本会自动管理 Cookie：
- 首次运行时自动登录
- Cookie 保存到文件中
- Cookie 失效时自动重新登录

### Q: 为什么没有收到 Telegram 通知？

**A:** 检查：
1. `TG_BOT_TOKEN` 和 `TG_CHAT_ID` 是否正确
2. 是否先给 Bot 发送过消息（激活 Bot）
3. Bot Token 格式是否正确

### Q: GitHub Actions 无法运行？

**A:** 可能的原因：
1. 仓库是私有的，需要确保 Actions 已启用
2. Workflow 文件路径不对（应该在 `.github/workflows/` 目录下）
3. Secrets 没有正确配置
4. Actions 没有启用，需要手动 Enable

### Q: 如何查看签到记录？

**A:** 
- **本地运行**：查看 `tikhub_checkin_record.json` 文件
- **GitHub Actions**：在 Actions 页面下载 Artifacts

### Q: 可以同时多个账号签到吗？

**A:** 需要分别 Fork 仓库或创建多个工作流文件。

### Q: 随机延迟是什么意思？

**A:** 自动运行模式下，脚本会随机延迟 1-60 秒再执行，避免：
- 所有用户同时请求导致服务器压力
- 被识别为机器人行为

### Q: 如何关闭自动运行？

**A:** 
1. 进入 `Actions` 页面
2. 点击左侧的 `TikHub 自动签到`
3. 点击右上角的 `...` 菜单
4. 选择 `Disable workflow`

## 🔐 安全说明

1. **账号密码安全**：
   - 密码保存在 GitHub Secrets 中，加密存储
   - 不会出现在日志中
   - 不会被其他人看到

2. **Cookie 安全**：
   - Cookie 保存在仓库的 Actions 缓存中
   - 只有你能访问
   - 定期会被清理

3. **建议**：
   - 不要在公开场合分享你的 Secrets
   - 定期更换密码
   - 使用强密码

## 📄 文件说明

```
├── .github/
│   └── workflows/
│       └── tikhub_checkin.yml    # GitHub Actions 工作流配置
├── tikhub_signin_playwright.py   # 主脚本（推荐使用）
├── tikhub_signin.py              # 简单版脚本（不推荐）
├── requirements.txt              # Python 依赖
├── README.md                     # 使用文档
├── tikhub_checkin_record.json    # 签到记录（自动生成）
└── tikhub_cookies.json           # Cookie 缓存（自动生成）
```

## 🎯 工作流程

1. **启动浏览器** - 无头模式启动 Chromium
2. **加载 Cookie** - 尝试加载已保存的 Cookie
3. **访问页面** - 访问 TikHub 用户概览页面
4. **检查登录** - 如果未登录，使用账号密码登录
5. **关闭弹窗** - 自动关闭推广弹窗
6. **查找签到按钮** - 多种方式查找签到按钮
7. **点击签到** - 执行签到操作
8. **等待完成** - 等待 reCAPTCHA 验证和签到完成
9. **保存 Cookie** - 保存 Cookie 供下次使用
10. **记录统计** - 更新签到记录
11. **发送通知** - 发送 Telegram 通知

## 🌟 更新日志

### v2.0.0 (2025-01-19)
- ✨ 完全重写脚本，支持 GitHub Actions
- ✨ 添加 Telegram 通知功能
- ✨ 添加签到记录统计
- ✨ 优化 Cookie 管理
- ✨ 优化错误处理
- ✨ 美化输出信息

### v1.0.0 (2025-01-18)
- 🎉 初始版本
- ✅ 基础签到功能

## 📜 许可证

本项目仅供学习交流使用，请勿用于商业用途。

## 🙏 鸣谢

- [Playwright](https://playwright.dev/) - 浏览器自动化工具
- [一言](https://hitokoto.cn/) - 每日一言 API
- HiFiNi 自动签到脚本 - 通知格式参考

## 💬 问题反馈

如有问题或建议，欢迎提 Issue。

---

⭐ 如果这个项目对你有帮助，欢迎 Star！
