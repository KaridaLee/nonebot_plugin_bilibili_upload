## bilibili视频、专栏上传QQ插件

### 安装方法
根据[nonebot v2官方文档]([https://nonebot.dev/docs/)部署nonebot框架到你的机器上  

在release里找到最新版本，将压缩包解压后安装到你的机器人项目中的plugins文件夹里  
非`nb run`指令启动项目的，需要按照文档新建一个bot.py来导入插件  
调试参数后重启项目即可使用  
__tips：建议机器人项目部署于python虚拟环境中__  

### 配置文件
config中有两个常用参数可以修改
```
bilibili_download_dir: str = "./bilibili_upload/plugins/bilibili_upload/Downloads"
bilibili_max_file_size: int = 200 * 1024 * 1024
```
`bilibili_download_dir`参数指定的是下载且处理完成的视频存放位置  
`bilibili_max_file_size`参数为发送最大视频大小，例如`200 * 1024 * 1024`指的是不超过200Mb  

### 需要的环境
安装ffmpeg，并在系统变量中添加  
需要安装的python依赖库  
`pip install pathlib httpx asyncio os re time requests typing subprocess json playwright html2image selenium`  

### 使用方法
直接在群里发送：BV号，b23分享链接，完整的视频链接  
例如：BV1kytazSEHE、https://www.bilibili.com/video/BV1kytazSEHE、https://b23.tv/1vfL3RX  
专栏也是同理，专栏需要发送完整链接  
等待片刻即可，处理速度与你的机器性能、网络有直接关系  
