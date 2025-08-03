import re
from typing import Optional

def extract_bv_from_url(text: str) -> Optional[str]:
    bv_pattern = r'BV[a-zA-Z0-9]{10}'
    bv_match = re.search(bv_pattern, text)
    if bv_match:
        return f"https://www.bilibili.com/video/{bv_match.group()}"
    url_patterns = [
        r'https?://www\.bilibili\.com/video/[a-zA-Z0-9?&=]+',
        r'https?://b23\.tv/[a-zA-Z0-9]+',
        r'https?://m\.bilibili\.com/video/[a-zA-Z0-9?&=]+',
        r'https?://bilibili\.com/video/[a-zA-Z0-9?&=]+',
    ]
    
    for pattern in url_patterns:
        match = re.search(pattern, text)
        if match:
            url = match.group()
            if 'b23.tv' in url:
                resolved_url = resolve_short_url(url)
                if 'bilibili.com/video/' in resolved_url:
                    return resolved_url
                else:
                    continue
            return url
    return None

def extract_opus_from_url(text: str) -> Optional[str]:
    opus_patterns = [
        r'https?://www\.bilibili\.com/opus/\d+',
        r'https?://t\.bilibili\.com/\d+',
    ]
    for pattern in opus_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()
    return None

def resolve_short_url(url: str) -> str:
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        return response.url
    except Exception:
        try:
            response = requests.get(url, headers=headers, allow_redirects=True, timeout=10, stream=True)
            return response.url
        except Exception:
            return url

def is_bilibili_content(text: str) -> bool:
    return extract_bv_from_url(text) is not None or extract_opus_from_url(text) is not None
def get_bilibili_content_type(text: str) -> Optional[str]:
    if extract_bv_from_url(text):
        return "video"
    elif extract_opus_from_url(text):
        return "opus"
    return None