#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikHub 自动签到脚本
使用 Cookie 方式签到
"""

import asyncio
from playwright.async_api import async_playwright
import json
import os
import sys
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

# 每日一言API
DAILY_QUOTES_API = "https://v1.hitokoto.cn/?encode=json&c=k"


def get_beijing_time():
    """获取北京时间（UTC+8）"""
    return datetime.now(timezone(timedelta(hours=8)))


class TikHubCheckin:
    def __init__(self, cookie: str):
        """
        初始化签到类
        :param cookie: 登录后的cookie字符串
        """
        self.cookie = cookie
        self.base_url = "https://user.tikhub.io"
        
        # 签到相关属性
        self.login_method = "Cookie"
        self.points_gained = ""
        self.last_checkin_result = ""
        self.checkin_method = "Cookie签到"
        self.signin_success = False
        
        # API响应数据
        self.api_response_data = {}
        
        # 文件路径
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.checkin_record_file = os.path.join(app_dir, "tikhub_checkin_record.json")
    
    def parse_cookie_string(self, cookie_string):
        """将cookie字符串解析为Playwright需要的格式"""
        cookies = []
        for item in cookie_string.split('; '):
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.tikhub.io',
                    'path': '/'
                })
        return cookies
    
    async def checkin(self) -> Dict[str, any]:
        """执行签到"""
        try:
            print("=" * 80)
            print("TikHub 自动签到")
            print("=" * 80)
            
            async with async_playwright() as p:
                # 启动浏览器（GitHub Actions需要无头模式）
                is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
                print(f"\n[步骤 1] 启动浏览器{'（无头模式）' if is_github_actions else ''}...")
                
                browser = await p.chromium.launch(
                    headless=is_github_actions,  # GitHub Actions自动使用无头模式
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu'
                    ]
                )
                
                # 创建浏览器上下文
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
                )
                
                # 使用提供的Cookie
                print("[步骤 2] 注入Cookie...")
                cookies = self.parse_cookie_string(self.cookie)
                await context.add_cookies(cookies)
                
                # 创建新页面
                page = await context.new_page()
                
                # 监听API响应
                async def handle_response(response):
                    if 'daily_checkin' in response.url or 'checkin' in response.url:
                        print(f"\n{'='*60}")
                        print(f"📡 签到API响应")
                        print(f"{'='*60}")
                        print(f"请求URL: {response.url}")
                        print(f"状态码: {response.status}")
                        
                        try:
                            body = await response.json()
                            print(f"\n完整响应内容:")
                            print(json.dumps(body, ensure_ascii=False, indent=2))
                            
                            # 保存响应数据
                            self.api_response_data = body
                            
                            # 解析并显示关键信息
                            print(f"\n{'='*60}")
                            print("📊 签到结果详情")
                            print(f"{'='*60}")
                            
                            if response.status == 200:
                                if body.get('status') == 'success' or body.get('code') == 0 or body.get('success') == True:
                                    print("✅ 签到成功！")
                                    self.signin_success = True
                                    self.last_checkin_result = "签到成功"
                                    
                                    # 提取积分信息
                                    if 'points' in body:
                                        self.points_gained = str(body['points'])
                                        print(f"   🎁 获得积分: {self.points_gained}")
                                    if 'credits' in body:
                                        self.points_gained = str(body['credits'])
                                        print(f"   🎁 获得积分: {self.points_gained}")
                                    
                                    # 显示消息
                                    if 'message' in body:
                                        self.last_checkin_result = body['message']
                                        print(f"   💬 消息: {body['message']}")
                                    if 'msg' in body:
                                        self.last_checkin_result = body['msg']
                                        print(f"   💬 消息: {body['msg']}")
                                    
                                elif body.get('status') == 'error' or (body.get('code') and body.get('code') != 0):
                                    print("❌ 签到失败")
                                    msg = body.get('message') or body.get('msg') or body.get('error') or '未知错误'
                                    self.last_checkin_result = msg
                                    print(f"   ❗ 原因: {msg}")
                                    
                                    # 检查是否是已签到
                                    if '已签到' in msg or 'already' in msg.lower():
                                        self.signin_success = True
                                        self.checkin_method = "今日已签到"
                                else:
                                    print(f"📢 签到结果:")
                                    for key, value in body.items():
                                        print(f"   • {key}: {value}")
                            else:
                                print(f"❌ 签到失败: HTTP {response.status}")
                                
                            print(f"{'='*60}\n")
                            
                        except Exception as e:
                            print(f"\n⚠️ 解析响应失败: {e}")
                
                page.on('response', handle_response)
                
                try:
                    # 访问概览页面
                    print("[步骤 3] 访问用户概览页面...")
                    await page.goto(f'{self.base_url}/zh-hans/users/overview', wait_until='networkidle', timeout=60000)
                    await asyncio.sleep(2)
                    
                    # 检查是否需要登录
                    if 'login' in page.url.lower():
                        print("❌ Cookie已失效，请更新Cookie")
                        return {"success": False, "message": "Cookie已失效，请重新获取Cookie"}
                    
                    # 关闭弹窗
                    print("[步骤 4] 检查并关闭可能的弹窗...")
                    await self._close_popups(page)
                    
                    # 检查是否已签到
                    print("[步骤 5] 检查签到状态...")
                    page_content = await page.content()
                    if '已签到' in page_content or 'Already checked' in page_content:
                        print("✅ 检测到已签到状态")
                        self.signin_success = True
                        self.last_checkin_result = "今日已签到"
                        self.checkin_method = "今日已签到"
                    
                    # 查找并点击签到按钮
                    if not self.signin_success:
                        print("[步骤 6] 查找签到按钮...")
                        signin_button = await self._find_signin_button(page)
                        
                        if signin_button:
                            print("[步骤 7] 点击签到按钮...")
                            await signin_button.click()
                            
                            # 等待签到完成
                            print("⏳ 等待签到完成...")
                            await asyncio.sleep(8)
                        else:
                            print("⚠️ 未找到签到按钮")
                    
                    # 保存签到记录
                    if self.signin_success:
                        self._save_checkin_record()
                    
                    # 截图
                    if not is_github_actions:
                        await page.screenshot(path='tikhub_final.png', full_page=True)
                        print("📸 已保存截图")
                    
                except Exception as e:
                    print(f"\n❌ 执行过程中出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return {"success": False, "message": f"执行出错: {str(e)}"}
                
                finally:
                    await browser.close()
            
            # 返回结果
            if self.signin_success:
                return {"success": True, "message": self.last_checkin_result}
            else:
                return {"success": False, "message": self.last_checkin_result or "签到失败"}
                
        except Exception as e:
            error_msg = f"签到过程发生错误: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "message": error_msg}
    
    async def _close_popups(self, page):
        """关闭弹窗"""
        close_selectors = [
            'button[aria-label="Close"]',
            'button[class*="close"]',
            'button:has-text("不再提醒")',
            'button:has-text("关闭")',
            '.modal-close'
        ]
        
        for selector in close_selectors:
            try:
                close_btn = await page.wait_for_selector(selector, timeout=2000)
                if close_btn and await close_btn.is_visible():
                    await close_btn.click()
                    await asyncio.sleep(1)
                    print("✅ 已关闭弹窗")
                    break
            except:
                continue
        
        # 尝试ESC键
        try:
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
        except:
            pass
    
    async def _find_signin_button(self, page):
        """查找签到按钮"""
        selectors = [
            'button:has-text("签到")',
            'a:has-text("签到")',
            'button:has-text("Check in")',
            'button:has-text("每日签到")',
            '#checkin-button',
            '.checkin-btn'
        ]
        
        for selector in selectors:
            try:
                button = await page.wait_for_selector(selector, timeout=2000)
                if button and await button.is_visible():
                    print(f"✅ 找到签到按钮: {selector}")
                    return button
            except:
                continue
        
        return None
    
    def _save_checkin_record(self):
        """保存签到记录"""
        try:
            beijing_time = get_beijing_time()
            today = beijing_time.strftime('%Y-%m-%d')
            month = beijing_time.strftime('%Y-%m')
            year = beijing_time.strftime('%Y')
            
            # 加载现有记录
            if os.path.exists(self.checkin_record_file):
                with open(self.checkin_record_file, 'r', encoding='utf-8') as f:
                    try:
                        record = json.load(f)
                    except json.JSONDecodeError:
                        record = {"total": 0, "years": {}}
            else:
                record = {"total": 0, "years": {}}
            
            # 确保年份存在
            if year not in record["years"]:
                record["years"][year] = {"total": 0, "months": {}}
            
            # 确保月份存在
            if month not in record["years"][year]["months"]:
                record["years"][year]["months"][month] = {"total": 0, "days": []}
            
            # 检查今天是否已经签到
            days = record["years"][year]["months"][month]["days"]
            
            # 新签到情况下更新记录
            if today not in days:
                days.append(today)
                record["total"] += 1
                record["years"][year]["total"] += 1
                record["years"][year]["months"][month]["total"] += 1
                
                record["years"][year]["months"][month]["days"] = days
                print(f"📊 签到记录已更新: 总计{record['total']}天，本月{len(days)}天")
            
            # 保存记录文件
            with open(self.checkin_record_file, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            
            return record
        except Exception as e:
            print(f"❌ 保存签到记录失败: {e}")
            return {"total": 0, "years": {}}
    
    def _get_checkin_statistics(self):
        """获取签到统计信息"""
        try:
            if os.path.exists(self.checkin_record_file):
                with open(self.checkin_record_file, 'r', encoding='utf-8') as f:
                    try:
                        record = json.load(f)
                        
                        beijing_time = get_beijing_time()
                        current_year = beijing_time.strftime('%Y')
                        current_month = beijing_time.strftime('%Y-%m')
                        today = beijing_time.strftime('%Y-%m-%d')
                        
                        total_days = record.get("total", 0)
                        
                        month_data = record.get("years", {}).get(current_year, {}).get("months", {}).get(current_month, {})
                        month_days = len(month_data.get("days", []))
                        
                        is_first_today = today in month_data.get("days", [])
                        
                        return {
                            "total_days": total_days,
                            "month_days": month_days,
                            "is_first_today": is_first_today
                        }
                    except json.JSONDecodeError:
                        pass
            
            return {
                "total_days": 0,
                "month_days": 0,
                "is_first_today": False
            }
        except Exception as e:
            print(f"❌ 获取签到统计信息失败: {e}")
            return {
                "total_days": 0,
                "month_days": 0,
                "is_first_today": False
            }
    
    def send_telegram_notification(self, tg_bot_token: str, tg_chat_id: str, message: str):
        """发送Telegram通知"""
        if not tg_bot_token or not tg_chat_id:
            print("⚠️ Telegram Bot Token或Chat ID为空，跳过通知")
            return
        
        try:
            # 获取当前日期和时间（北京时间）
            now = get_beijing_time()
            date_str = now.strftime("%Y年%m月%d日")
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            weekday = weekdays[now.weekday()]
            time_str = now.strftime("%H:%M:%S")
            
            # 获取签到统计
            stats = self._get_checkin_statistics()
            total_days = stats["total_days"]
            month_days = stats["month_days"]
            is_first_today = stats["is_first_today"]
            
            # 构建签到统计信息
            month_name = now.strftime("%m月")
            stats_text = f"  · 总计已签到: {total_days} 天\n  · {month_name}已签到: {month_days} 天"
            if is_first_today:
                stats_text += "\n  · 今日首次签到 🆕"
            
            # 获取登录方式
            login_method_icon = "🍪"
            login_method_text = f"{login_method_icon} 登录方式: {self.login_method}"
            
            # 随机选择一条激励语
            mottos = [
                "打卡成功！向着梦想飞奔吧~",
                "坚持签到，未来可期！",
                "今日已签到，继续保持！",
                "打卡完成，享受TikHub服务！",
                "签到成功，美好的一天开始了！",
                "打卡成功，每天进步一点点！",
                "签到打卡，从未间断！",
                "又是美好的一天，签到成功！"
            ]
            motto = random.choice(mottos)
            
            # 获取每日一言
            try:
                response = requests.get(DAILY_QUOTES_API, timeout=5)
                if response.status_code == 200:
                    hitokoto_data = response.json()
                    quote = f"{hitokoto_data.get('hitokoto', '')} —— {hitokoto_data.get('from_who', '佚名') or '佚名'}"
                else:
                    raise Exception(f"API返回状态码: {response.status_code}")
            except Exception as e:
                print(f"⚠️ 获取每日一言失败: {str(e)}，使用备用格言")
                quotes = [
                    "不要等待，时机永远不会恰到好处。 —— 拿破仑·希尔",
                    "合理安排时间，就等于节约时间。 —— 培根",
                    "行动是治愈恐惧的良药。 —— 戴尔·卡耐基",
                    "成功是一段路程，而非终点。 —— 本·斯威特兰"
                ]
                quote = random.choice(quotes)
            
            # 获取签到状态
            if self.signin_success:
                if "已签到" in message or "已签到" in self.last_checkin_result:
                    status = "今日已签到"
                    icon = "✓"
                    header_icon = "🔄"
                else:
                    status = self.last_checkin_result
                    icon = "✅"
                    header_icon = "✨"
            else:
                status = "签到失败"
                icon = "❌"
                header_icon = "⚠️"
            
            # 获取积分信息
            points_text = ""
            if self.points_gained:
                points_text = f"💎 本次获得: +{self.points_gained} 积分\n"
            
            # 构建签到方式显示
            checkin_method_icon = "🍪"
            
            # 构建美化的消息
            formatted_message = f"""{header_icon} *TikHub每日签到* {header_icon}

📅 日期: {date_str} ({weekday})
🕒 时间: {time_str}
👤 账号: Cookie用户
{icon} 状态: {status}
{login_method_text}
{checkin_method_icon} 签到方式: {self.checkin_method}
{points_text}
📊 签到统计:
{stats_text}

🚀 {motto}

📝 每日一言: {quote}"""
            
            url = f"https://api.telegram.org/bot{tg_bot_token}/sendMessage"
            data = {
                "chat_id": tg_chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print("✅ Telegram通知发送成功")
            else:
                print(f"❌ Telegram通知发送失败: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"❌ 发送Telegram通知出错: {str(e)}")


def main():
    """主函数"""
    print("=" * 80)
    print("TikHub 自动签到脚本")
    print("=" * 80)
    
    # 检查是否自动运行（定时任务）
    is_auto_run = os.environ.get("IS_AUTO_RUN", "false").lower() in ["true", "1", "yes"]
    
    # 如果是自动运行，添加随机延迟（1-60秒）
    if is_auto_run:
        delay_seconds = random.randint(1, 60)
        print(f"🕒 自动运行模式，随机延迟 {delay_seconds} 秒后开始签到...")
        beijing_time = get_beijing_time()
        print(f"⏰ 预计开始时间: {(beijing_time + timedelta(seconds=delay_seconds)).strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(delay_seconds)
        print(f"✅ 延迟结束，开始执行签到")
        print("-" * 80)
    else:
        print("🖐️ 手动运行模式，立即开始签到")
        print("-" * 80)
    
    # 从环境变量获取配置
    cookie = os.environ.get("TIKHUB_COOKIE")
    
    # 获取Telegram配置
    tg_bot_token = os.environ.get("TG_BOT_TOKEN")
    tg_chat_id = os.environ.get("TG_CHAT_ID")
    
    # 检查配置
    if not cookie:
        print("❌ 错误: 未设置 Cookie")
        print("\n请配置 TIKHUB_COOKIE：")
        print("  在 GitHub Secrets 中添加：")
        print("  - TIKHUB_COOKIE: 你的 Cookie 字符串")
        print("\n如何获取 Cookie：")
        print("  1. 在浏览器中登录 TikHub")
        print("  2. 打开开发者工具（F12）")
        print("  3. 切换到 Network 标签")
        print("  4. 刷新页面")
        print("  5. 找到任意请求，查看 Request Headers")
        print("  6. 复制 Cookie 字段的完整值")
        print("\n可选：Telegram通知")
        print("  - TG_BOT_TOKEN: Telegram Bot Token")
        print("  - TG_CHAT_ID: Telegram Chat ID")
        sys.exit(1)
    
    # 创建签到实例
    print(f"📝 使用 Cookie 签到")
    print(f"🍪 Cookie 长度: {len(cookie)}")
    checkin = TikHubCheckin(cookie=cookie)
    
    # 执行签到
    result = asyncio.run(checkin.checkin())
    
    # 输出结果
    print("\n" + "=" * 80)
    print("签到结果:")
    print(f"状态: {'✅ 成功' if result['success'] else '❌ 失败'}")
    print(f"信息: {result['message']}")
    print("=" * 80)
    
    # 发送Telegram通知
    if tg_bot_token and tg_chat_id:
        print("\n📱 正在发送Telegram通知...")
        checkin.send_telegram_notification(tg_bot_token, tg_chat_id, result['message'])
    
    # 如果失败，退出码为1
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
