import requests
import re
import json
import os
import subprocess
from typing import Optional, Tuple
from .config import Config

plugin_config = Config()

def clean_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def get_bilibili_page(url: str) -> requests.Response:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': url
    }
    
    if 'b23.tv' in url:
        try:
            head_response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            url = head_response.url
            print(f'>>>解析后的URL: {url}')
        except Exception as e:
            print(f'>>>短链接解析失败，尝试直接访问: {e}')
    
    response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    response.raise_for_status()
    return response

def merge_audio_video(video_path, audio_path, output_path):
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    
    except FileNotFoundError:
        raise Exception("未找到ffmpeg")
    except Exception as e:
        raise Exception(f"合并时错误：{str(e)}")

def cleanup_temp_files(video_path, audio_path):
    try:
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception:
        pass

def download_bilibili_video(url: str, download_dir: str) -> Tuple[bool, str, Optional[str]]:
    download_dir = plugin_config.bilibili_download_dir
    try:
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        head = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.67',
            'Referer': url
        }

        resp = requests.get(url, headers=head, timeout=30)
        resp.raise_for_status()

        title_match = re.findall('<h1.*?>(.*?)</h1>', resp.text)
        if not title_match:
            return False, "无法提取视频标题", None
        
        title = clean_filename(title_match[0])
        
        json_match = re.findall('<script>window.__playinfo__=(.*?)</script>', resp.text)
        if not json_match:
            return False, "无法找到视频信息", None
        
        json_data = json.loads(json_match[0])

        audio_path = os.path.join(download_dir, f"{title}_temp.mp3")
        video_path = os.path.join(download_dir, f"{title}_temp.mp4")
        output_path = os.path.join(download_dir, f"{title}.mp4")

        if os.path.exists(output_path):
            return True, f"视频已存在: {title}", output_path

        # 安全获取音频URL
        audio_url = get_media_url(json_data, 'audio')
        if not audio_url:
            return False, "无法获取音频流", None
            
        audio_data = requests.get(audio_url, headers=head, timeout=60)
        audio_data.raise_for_status()
        
        with open(audio_path, mode='wb') as f:
            f.write(audio_data.content)

        # 安全获取视频URL
        video_url = get_media_url(json_data, 'video')
        if not video_url:
            cleanup_temp_files(video_path, audio_path)
            return False, "无法获取视频流", None
            
        video_data = requests.get(video_url, headers=head, timeout=60)
        video_data.raise_for_status()
        
        with open(video_path, mode='wb') as f:
            f.write(video_data.content)

        if merge_audio_video(video_path, audio_path, output_path):
            cleanup_temp_files(video_path, audio_path)
            return True, f"下载完成: {title}", output_path
        else:
            cleanup_temp_files(video_path, audio_path)
            return False, "音视频合并失败", None

    except requests.RequestException as e:
        return False, f"网络请求错误: {str(e)}", None
    except json.JSONDecodeError as e:
        return False, f"JSON解析错误: {str(e)}", None
    except KeyError as e:
        return False, f"数据结构错误: {str(e)}", None
    except Exception as e:
        return False, f"未知错误: {str(e)}", None
    
def get_media_url(json_data: dict, media_type: str) -> Optional[str]:
    try:
        media_list = json_data['data']['dash'][media_type]
        if not media_list:
            return None
            
        # 按优先级尝试不同的索引
        indices_to_try = [2, 1, 0, -1]  # 优先尝试索引2，然后1，0，最后一个
        
        for index in indices_to_try:
            try:
                if index == -1:
                    # 尝试最后一个元素
                    media_item = media_list[-1]
                else:
                    # 检查索引是否在范围内
                    if index < len(media_list):
                        media_item = media_list[index]
                    else:
                        continue
                
                # 尝试获取URL，优先使用backupUrl，然后baseUrl
                url = None
                if 'backupUrl' in media_item and media_item['backupUrl']:
                    url = media_item['backupUrl'][0]
                elif 'baseUrl' in media_item and media_item['baseUrl']:
                    url = media_item['baseUrl']
                
                if url:
                    print(f">>>成功获取{media_type}流，索引: {index}, URL: {url[:50]}...")
                    return url
                    
            except (IndexError, KeyError, TypeError):
                continue
        
        # 如果所有尝试都失败，返回None
        print(f">>>无法获取{media_type}流，所有索引都失败")
        return None
        
    except KeyError as e:
        print(f">>>获取{media_type}流时缺少必要字段: {e}")
        return None
    except Exception as e:
        print(f">>>获取{media_type}流时发生未知错误: {e}")
        return None