import re
from typing import Optional

def extract_bv_from_url(text: str) -> Optional[str]:
    # 首先尝试提取完整的B站URL
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
    
    # 只有在没有找到完整URL的情况下，才尝试提取BV号
    # 并且要求BV号前后有特定的分隔符或位于字符串边界
    bv_pattern = r'(?:^|[\s\[\]()（）【】<>《》""''`~!@#$%^&*+=|\\:;,.\?/])(BV[1-9A-NP-Za-km-z]{10})(?=[\s\[\]()（）【】<>《》""''`~!@#$%^&*+=|\\:;,.\?/]|$)'
    bv_match = re.search(bv_pattern, text)
    if bv_match:
        bv_id = bv_match.group(1)
        # 额外验证：确保BV号符合B站的编码规则
        if is_valid_bv_id(bv_id):
            return f"https://www.bilibili.com/video/{bv_id}"
    
    return None

def is_valid_bv_id(bv_id: str) -> bool:
    """
    验证BV号是否符合B站的编码规则
    B站BV号使用base58编码，不包含 0, O, I, l 等容易混淆的字符
    """
    if not bv_id.startswith('BV') or len(bv_id) != 12:
        return False
    
    # B站BV号的有效字符集（base58）
    valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
    bv_content = bv_id[2:]  # 去掉"BV"前缀
    
    # 检查是否所有字符都在有效字符集中
    return all(char in valid_chars for char in bv_content)

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
    """
    更严格的B站内容检测
    """
    # 首先检查是否包含明显的B站URL
    if re.search(r'https?://(?:www\.|m\.)?bilibili\.com/', text) or \
       re.search(r'https?://b23\.tv/', text) or \
       re.search(r'https?://t\.bilibili\.com/', text):
        return True
    
    # 然后检查BV号，但要更严格
    extracted_url = extract_bv_from_url(text)
    if extracted_url:
        return True
        
    # 检查专栏链接
    if extract_opus_from_url(text):
        return True
        
    return False

def get_bilibili_content_type(text: str) -> Optional[str]:
    if extract_bv_from_url(text):
        return "video"
    elif extract_opus_from_url(text):
        return "opus"
    return None

def is_likely_false_positive(text: str) -> bool:
    """
    检测可能的误识别情况
    """
    # 如果消息很短且包含特殊字符，可能是表情包
    if len(text.strip()) < 20 and re.search(r'[\[\]()（）【】<>《》""'']', text):
        return True
    
    # 如果包含大量特殊字符，可能是表情包代码
    special_char_count = len(re.findall(r'[^\w\s\u4e00-\u9fff]', text))
    if special_char_count > len(text) * 0.3:  # 特殊字符占比超过30%
        return True
    
    return False