import asyncio
import os
import re
import httpx
import time
from pathlib import Path
from nonebot import on_message
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot.log import logger
from .config import Config
from .utils import is_bilibili_content, extract_bv_from_url, is_likely_false_positive
from .bilibili_videos import download_bilibili_video
from .bilibili_opus import convert_opus_to_image

__plugin_meta__ = PluginMetadata(
    name="bilibili_upload",
    description="B站视频下载和专栏截图插件",
    usage="发送包含BV号、B站视频链接或专栏链接的消息即可自动处理",
    config=Config,
)

plugin_config = Config()

bilibili_matcher = on_message(priority=10, block=False)

@bilibili_matcher.handle()
async def handle_bilibili(bot: Bot, event: MessageEvent):
    message_text = str(event.get_message())
    
    # 添加误识别检测
    if is_likely_false_positive(message_text):
        return
    
    # 专栏处理逻辑保持不变
    if any(pattern in message_text for pattern in ['bilibili.com/opus/', 't.bilibili.com/']):
        url_match = re.search(r'https?://(?:www\.bilibili\.com/opus/|t\.bilibili\.com/)\d+', message_text)
        if url_match:
            opus_url = url_match.group()
            await bilibili_matcher.send("正在转换专栏喵~")
            try:
                success, message, file_path = await convert_opus_to_image(
                    opus_url, 
                    plugin_config.bilibili_download_dir
                )
                if success and file_path:
                    file_size = os.path.getsize(file_path)
                    if file_size > plugin_config.bilibili_max_file_size:
                        await bilibili_matcher.send(
                            f"专栏截图完成，但文件过大({file_size / 1024 / 1024:.1f}MB)，无法发送到群聊\n"
                            f"文件保存在: {file_path}"
                        )
                    else:
                        image_segment = MessageSegment.image(Path(file_path))
                        await bilibili_matcher.send(
                            MessageSegment.text(f"完成了喵: {message}\n") + image_segment
                        )
                else:
                    await bilibili_matcher.send(f"专栏转换失败: {message}")
                    
            except Exception as e:
                logger.error(f"专栏转换出错: {e}")
                await bilibili_matcher.send(f"专栏转换过程中出现错误: {str(e)}")
            return
    
    # 检查是否为B站视频内容
    if not is_bilibili_content(message_text):
        return
        
    url = extract_bv_from_url(message_text)
    if not url:
        return
        
    image_path = None

    try:
        # 创建图片保存目录（如果不存在）
        image_dir = os.path.join(plugin_config.bilibili_download_dir, "images")
        os.makedirs(image_dir, exist_ok=True)

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get("https://t.alcy.cc/xhl")
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'webp' in content_type or response.url.path.endswith('.webp'):
                    ext = '.webp'
                # 生成唯一的文件名
                timestamp = int(time.time())
                image_path = os.path.join(image_dir, f"temp_image_{timestamp}{ext}")

                # 保存图片到本地
                with open(image_path, "wb") as f:
                    f.write(response.content)

                # 构建带图片的消息
                image_segment = MessageSegment.image(Path(image_path))
                message_with_image = MessageSegment.text("正在下载了喵~") + image_segment
                await bilibili_matcher.send(message_with_image)
            else:
                logger.warning(f"获取图片失败，状态码: {response.status_code}, 最终URL: {response.url}")
                await bilibili_matcher.send("正在下载了喵~")
    except Exception as e:
        logger.error(f"获取图片失败: {e}")
        await bilibili_matcher.send("正在下载了喵~")
    
    try:
        loop = asyncio.get_event_loop()
        success, message, file_path = await loop.run_in_executor(
            None, 
            download_bilibili_video, 
            url, 
            plugin_config.bilibili_download_dir
        )
        
        if success and file_path:
            file_size = os.path.getsize(file_path)
            if file_size > plugin_config.bilibili_max_file_size:
                await bilibili_matcher.send(
                    f"下载完成，但文件过大({file_size / 1024 / 1024:.1f}MB)，无法发送到群聊\n"
                    f"文件保存在: {file_path}"
                )
            else:
                video_segment = MessageSegment.video(Path(file_path))
                await bilibili_matcher.send(
                    MessageSegment.text(f"下载完成: {message}\n") + video_segment
                )
        else:
            await bilibili_matcher.send(f"下载失败: {message}")
            
    except Exception as e:
        logger.error(f"B站视频下载出错: {e}")
        await bilibili_matcher.send(f"下载过程中出现错误: {str(e)}")