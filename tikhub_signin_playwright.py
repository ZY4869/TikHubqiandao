#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikHub 自动签到脚本
使用 Cookie 方式签到
"""

import asyncio
import sys
import io

# 设置 Windows 控制台输出编码为 UTF-8
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

from playwright.async_api import async_playwright
import json
import os
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
                    await page.goto(f'{self.base_url}/zh-hans/users/overview', wait_until='domcontentloaded', timeout=30000)
                    print("   页面已加载，等待内容渲染...")
                    await asyncio.sleep(3)
                    
                    # 检查是否需要登录
                    print(f"   当前URL: {page.url}")
                    if 'login' in page.url.lower():
                        print("❌ Cookie已失效，请更新Cookie")
                        return {"success": False, "message": "Cookie已失效，请重新获取Cookie"}
                    
                    # 检查页面标题
                    page_title = await page.title()
                    print(f"   页面标题: {page_title}")
                    
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
                            
                            # 等待签到完成或验证码出现
                            print("⏳ 等待签到完成...")
                            await asyncio.sleep(3)
                            
                            # 检查是否有验证码
                            print("[步骤 8] 检查验证码...")
                            captcha_handled = await self._handle_captcha(page)
                            
                            if captcha_handled:
                                print("✅ 验证码已处理，等待签到结果...")
                                await asyncio.sleep(5)
                            else:
                                # 没有验证码或无法处理，继续等待
                                await asyncio.sleep(5)
                        else:
                            print("⚠️ 未找到签到按钮")
                            # 保存调试截图
                            try:
                                screenshot_path = 'tikhub_debug.png'
                                await page.screenshot(path=screenshot_path, full_page=True)
                                print(f"📸 已保存调试截图: {screenshot_path}")
                            except Exception as e:
                                print(f"⚠️ 保存调试截图失败: {e}")
                    
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
        # 多种弹窗关闭选择器
        close_selectors = [
            'button:has-text("不再显示")',  # "重磅好消息"弹窗
            'button:has-text("稍后提醒我")',
            'button:has-text("不再提醒")',
            'button:has-text("关闭")',
            'button[aria-label="Close"]',
            'button[class*="close"]',
            '.modal-close',
            'button:has-text("我知道了")',
            'button:has-text("确定")',
            # 尝试找 X 按钮
            'button svg[class*="close"]',
            '[class*="modal"] button[class*="close"]',
        ]
        
        popup_closed = False
        for selector in close_selectors:
            try:
                close_btn = await page.wait_for_selector(selector, timeout=2000)
                if close_btn and await close_btn.is_visible():
                    print(f"   找到弹窗关闭按钮: {selector}")
                    await close_btn.click()
                    await asyncio.sleep(1.5)
                    print("✅ 已关闭弹窗")
                    popup_closed = True
                    break
            except:
                continue
        
        # 尝试ESC键
        if not popup_closed:
            try:
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
                print("✅ 已尝试使用 ESC 键关闭弹窗")
            except:
                pass
    
    async def _find_signin_button(self, page):
        """查找签到按钮"""
        # 先保存页面HTML用于调试（仅在GitHub Actions中）
        is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
        if is_github_actions:
            try:
                html_content = await page.content()
                # 查找是否有"签到"相关文本
                if '签到' in html_content:
                    print("   ✓ 页面HTML中包含'签到'文字")
                    # 提取包含"签到"的部分内容（用于调试）
                    import re
                    matches = re.findall(r'.{0,50}签到.{0,50}', html_content)
                    if matches:
                        print(f"   找到{len(matches)}处'签到'文字:")
                        for i, match in enumerate(matches[:3]):  # 只显示前3个
                            print(f"     {i+1}. {match.strip()}")
                else:
                    print("   ✗ 页面HTML中未找到'签到'文字")
            except Exception as e:
                print(f"   调试信息获取失败: {e}")
        
        selectors = [
            # TikHub 特定的签到按钮选择器
            'div[name="checkedin"]',
            'div[data-tip="点击签到"]',
            # 备用通用选择器
            'button:has-text("签到")',
            'a:has-text("签到")',
            '[role="button"]:has-text("签到")',
            'button:has-text("Check in")',
            'button:has-text("每日签到")',
            'a:has-text("每日签到")',
            '#checkin-button',
            '.checkin-btn',
        ]
        
        print("   尝试查找签到按钮...")
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.inner_text()
                        text = text.strip()
                        # 只匹配文本较短的元素（避免匹配整个页面容器）
                        if len(text) <= 20 and ('签到' in text or 'check' in text.lower()):
                            print(f"✅ 找到签到按钮: {selector} (文本: {text})")
                            return element
            except Exception as e:
                continue
        
        # 最后尝试：通过页面内容查找所有包含"签到"的可点击元素
        print("   使用备用方法查找...")
        try:
            # 查找所有可能的可点击元素
            all_elements = await page.query_selector_all('button, a, [role="button"], div[onclick], [class*="button"], [class*="btn"]')
            for element in all_elements:
                try:
                    if await element.is_visible():
                        text = await element.inner_text()
                        # 只匹配文本简短且包含"签到"的元素
                        if text and len(text.strip()) <= 20 and '签到' in text:
                            print(f"✅ 找到签到元素 (文本: {text.strip()})")
                            return element
                except:
                    continue
        except:
            pass
        
        # 最终尝试：直接通过 XPath 查找
        print("   使用 XPath 查找...")
        try:
            xpath_selectors = [
                "//button[contains(text(), '签到')]",
                "//a[contains(text(), '签到')]",
                "//*[contains(@class, 'button') and contains(text(), '签到')]",
                "//*[contains(@class, 'btn') and contains(text(), '签到')]"
            ]
            for xpath in xpath_selectors:
                try:
                    element = await page.query_selector(f"xpath={xpath}")
                    if element and await element.is_visible():
                        text = await element.inner_text()
                        if len(text.strip()) <= 20:
                            print(f"✅ 通过 XPath 找到签到按钮 (文本: {text.strip()})")
                            return element
                except:
                    continue
        except:
            pass
        
        return None
    
    async def _handle_captcha(self, page):
        """处理验证码"""
        try:
            # 检查是否有验证码iframe或弹窗
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="captcha"]',
                '[class*="captcha"]',
                '[id*="captcha"]',
                '[class*="verify"]',
                '[id*="verify"]',
            ]
            
            for selector in captcha_selectors:
                try:
                    captcha_element = await page.query_selector(selector)
                    if captcha_element and await captcha_element.is_visible():
                        print(f"   检测到验证码元素: {selector}")
                        
                        # 如果是 reCAPTCHA
                        if 'recaptcha' in selector:
                            print("   检测到 reCAPTCHA，等待用户手动完成...")
                            # 在无头模式下无法处理 reCAPTCHA
                            is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
                            if is_github_actions:
                                print("   ⚠️ 无头模式无法自动处理 reCAPTCHA")
                                return False
                            else:
                                # 本地有头模式，等待用户手动完成
                                print("   请在浏览器中手动完成验证码...")
                                await asyncio.sleep(30)  # 给用户30秒时间
                                return True
                        
                        # 尝试简单的点击操作
                        print("   尝试点击验证码...")
                        await captcha_element.click()
                        await asyncio.sleep(2)
                        return True
                        
                except:
                    continue
            
            # 检查页面文本中是否提到验证码
            page_content = await page.content()
            if '验证码' in page_content or 'captcha' in page_content.lower() or 'verify' in page_content.lower():
                print("   ⚠️ 页面提示需要验证码，但未找到验证码元素")
                print("   可能的原因：")
                print("     1. 验证码在弹窗中但还未加载")
                print("     2. 使用了隐藏的验证码（如 hCaptcha）")
                print("     3. 需要更长的等待时间")
                
                # 再等待一下看验证码是否出现
                await asyncio.sleep(3)
                
                # 再次尝试查找
                for selector in captcha_selectors:
                    try:
                        captcha_element = await page.query_selector(selector)
                        if captcha_element and await captcha_element.is_visible():
                            print(f"   延迟检测到验证码: {selector}")
                            return False
                    except:
                        continue
            
            return False
            
        except Exception as e:
            print(f"   验证码处理出错: {e}")
            return False
    
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
    
    # 调试信息：检查环境变量
    print("🔍 环境变量检查:")
    print(f"  - TIKHUB_COOKIE 是否存在: {'是' if 'TIKHUB_COOKIE' in os.environ else '否'}")
    
    # 打印所有环境变量名称（用于调试）
    env_keys = [k for k in os.environ.keys() if 'TIKHUB' in k.upper() or 'TG_' in k.upper()]
    if env_keys:
        print(f"  - 找到的相关环境变量: {', '.join(env_keys)}")
    else:
        print(f"  - 未找到任何相关环境变量（包含 TIKHUB 或 TG_）")
    
    if cookie:
        print(f"  - Cookie 原始长度: {len(cookie)}")
        print(f"  - Cookie 去空格后长度: {len(cookie.strip())}")
        print(f"  - Cookie 前20个字符: {cookie[:20]}...")
        print(f"  - Cookie 是否包含 sessionid: {'是' if 'sessionid' in cookie else '否'}")
        print(f"  - Cookie 是否包含 csrftoken: {'是' if 'csrftoken' in cookie else '否'}")
        # 去除首尾空格和换行符
        cookie = cookie.strip()
    else:
        print(f"  - Cookie 值为: {repr(cookie)}")
        print(f"  - Cookie 的类型: {type(cookie)}")
    
    # 获取Telegram配置
    tg_bot_token = os.environ.get("TG_BOT_TOKEN")
    tg_chat_id = os.environ.get("TG_CHAT_ID")
    
    # 检查配置（确保不为空且去空格后仍有内容）
    if not cookie or len(cookie) == 0:
        print("❌ 错误: 未设置 Cookie 或 Cookie 为空")
        print("\n请检查以下配置：")
        print("  1. 确认在 GitHub Settings -> Secrets and variables -> Actions 中添加了 TIKHUB_COOKIE")
        print("  2. 确认 Secret 名称拼写正确（区分大小写）：TIKHUB_COOKIE")
        print("  3. 确认 Secret 值不为空，且不只包含空格")
        print("\n如何获取 Cookie：")
        print("  1. 在浏览器中登录 TikHub (https://user.tikhub.io)")
        print("  2. 打开开发者工具（F12）")
        print("  3. 切换到 Network 标签")
        print("  4. 刷新页面")
        print("  5. 找到任意请求，查看 Request Headers")
        print("  6. 复制 Cookie 字段的完整值")
        print("\n可选：Telegram通知")
        print("  - TG_BOT_TOKEN: Telegram Bot Token")
        print("  - TG_CHAT_ID: Telegram Chat ID")
        print("\n提示：确保 Cookie 值包含 session_id 或类似的认证信息")
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
