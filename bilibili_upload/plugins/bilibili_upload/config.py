from pydantic import BaseModel

class Config(BaseModel):
    bilibili_download_dir: str = "./bilibili_upload/plugins/bilibili_upload/Downloads"
    bilibili_max_file_size: int = 200 * 1024 * 1024  # 100MB大小限制