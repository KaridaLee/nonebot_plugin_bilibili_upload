import os
import re
import requests
import time
import asyncio
from typing import Optional, Tuple
from pathlib import Path
from .config import Config
from nonebot import get_plugin_config, get_driver
from nonebot.log import logger

plugin_config = Config()

# 使用playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# 使用html2image
try:
    from html2image import Html2Image
    HTML2IMAGE_AVAILABLE = True
except ImportError:
    HTML2IMAGE_AVAILABLE = False

# 使用selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

def clean_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def get_opus_page(url: str) -> requests.Response:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.bilibili.com/'
    }
    
    response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    response.raise_for_status()
    return response

async def screenshot_opus_playwright(url: str, output_path: str) -> bool:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            page = await browser.new_page(
                viewport={'width': 1200, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await page.wait_for_selector('.opus-detail', timeout=20000)
            await page.add_style_tag(content="""
                .bili-header, .nav-bar, .fixed-sidenav-storage, .palette-button-wrap,
                .opus-detail-footer, .comment-container, .right-sidebar-wrap,
                .floating-header, .ad-banner, .login-tip { display: none !important; }
                
                .opus-detail { 
                    margin: 0 !important; 
                    padding: 20px !important;
                    box-shadow: none !important;
                }
                
                body { 
                    background: white !important; 
                    margin: 0 !important;
                    padding: 0 !important;
                }
            """)
            
            content_height = await page.evaluate('''() => {
                const opus = document.querySelector('.opus-detail');
                return opus ? opus.scrollHeight : document.body.scrollHeight;
            }''')
            
            scroll_step = 800
            current_position = 0
            while current_position < content_height:
                current_position += scroll_step
                await page.evaluate(f'window.scrollTo(0, {current_position})')
                await asyncio.sleep(0.5)
                
            await page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(1)
            
            opus_element = await page.query_selector('.opus-detail')
            if opus_element:
                await opus_element.screenshot(
                    path=output_path, 
                    type='png',
                    timeout=60000
                )
            else:
                await page.screenshot(
                    path=output_path, 
                    full_page=True, 
                    type='png',
                    timeout=60000
                )
            
            await browser.close()
            return True
            
    except Exception as e:
        return False

def screenshot_opus_selenium(url: str, output_path: str) -> bool:
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1200,800')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        
        try:
            driver.get(url)
            
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "opus-detail")))
            
            driver.execute_script("""
                var style = document.createElement('style');
                style.innerHTML = `
                    .bili-header, .nav-bar, .fixed-sidenav-storage, .palette-button-wrap,
                    .opus-detail-footer, .comment-container, .right-sidebar-wrap,
                    .floating-header, .ad-banner, .login-tip { display: none !important; }
                    
                    .opus-detail { 
                        margin: 0 !important; 
                        padding: 20px !important;
                        box-shadow: none !important;
                    }
                    
                    body { 
                        background: white !important; 
                        margin: 0 !important;
                        padding: 0 !important;
                    }
                `;
                document.head.appendChild(style);
            """)
            
            content_height = driver.execute_script('''
                const opus = document.querySelector('.opus-detail');
                return opus ? opus.scrollHeight : document.body.scrollHeight;
            ''')
            
            scroll_step = 800
            current_position = 0
            while current_position < content_height:
                current_position += scroll_step
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(0.5)
                
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            try:
                opus_element = driver.find_element(By.CLASS_NAME, "opus-detail")
                opus_element.screenshot(output_path)
            except:
                driver.save_screenshot(output_path)
            
            return True
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Selenium截图失败: {e}")
        return False

def screenshot_opus_html2image(url: str, output_path: str) -> bool:
    try:
        response = get_opus_page(url)
        html_content = response.text
        style_injection = """
        <style>
        .bili-header, .nav-bar, .fixed-sidenav-storage, .palette-button-wrap,
        .opus-detail-footer, .comment-container, .right-sidebar-wrap,
        .floating-header, .ad-banner, .login-tip { display: none !important; }
        
        .opus-detail { 
            margin: 0 !important; 
            padding: 20px !important;
            box-shadow: none !important;
        }
        
        body { 
            background: white !important; 
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """

        html_content = html_content.replace('</head>', style_injection + '</head>')
        
        hti = Html2Image(size=(1200, 800))
        hti.screenshot(html_str=html_content, save_as=Path(output_path).name, css_str="")
        return True
        
    except Exception as e:
        print(f"Html2Image截图失败: {e}")
        return False

def extract_opus_info(html_content: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        title_match = re.search(r'<title>(.*?)</title>', html_content)
        title = title_match.group(1) if title_match else "未知标题"
        title = title.replace(' - 哔哩哔哩', '').strip()
        
        author_patterns = [
            r'"author":"([^"]+)"',
            r'"uname":"([^"]+)"',
            r'<span class="up-name">([^<]+)</span>',
        ]
        
        author = None
        for pattern in author_patterns:
            author_match = re.search(pattern, html_content)
            if author_match:
                author = author_match.group(1)
                break
        
        return title, author
        
    except Exception as e:
        return None, None

async def convert_opus_to_image(url: str, download_dir: str) -> Tuple[bool, str, Optional[str]]:
    download_dir = plugin_config.bilibili_download_dir
    try:
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
    
        response = get_opus_page(url)
        title, author = extract_opus_info(response.text)
        if not title:
            return False, "无法提取专栏标题", None
        
        title = clean_filename(title)
        author_info = f"_{clean_filename(author)}" if author else ""
        
        output_filename = f"opus_{title}{author_info}.png"
        output_path = os.path.join(download_dir, output_filename)
        
        if os.path.exists(output_path):
            return True, f"专栏图片已存在: {title}", output_path
        
        if author:
            print(f'>>>作者: {author}')
        screenshot_success = False
        
        if PLAYWRIGHT_AVAILABLE and not screenshot_success:
            screenshot_success = await screenshot_opus_playwright(url, output_path)
        
        if SELENIUM_AVAILABLE and not screenshot_success:
            screenshot_success = screenshot_opus_selenium(url, output_path)
        
        if HTML2IMAGE_AVAILABLE and not screenshot_success:
            screenshot_success = screenshot_opus_html2image(url, output_path)
        
        if screenshot_success and os.path.exists(output_path):
            return True, f" {title}", output_path
        else:
            return False, "所有截图方案都失败了，请检查依赖安装", None
            
    except requests.RequestException as e:
        return False, f"网络请求错误: {str(e)}", None
    except Exception as e:
        return False, f"未知错误: {str(e)}", None

def is_opus_url(url: str) -> bool:
    opus_patterns = [
        r'https?://www\.bilibili\.com/opus/\d+',
        r'https?://t\.bilibili\.com/\d+',
    ]
    
    for pattern in opus_patterns:
        if re.match(pattern, url):
            return True
    return False

def convert_opus_to_image_sync(url: str, download_dir: str) -> Tuple[bool, str, Optional[str]]:
    download_dir = plugin_config.bilibili_download_dir
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(convert_opus_to_image(url, download_dir))
    except Exception as e:
        return False, f"同步执行失败: {str(e)}", None
    finally:
        loop.close()