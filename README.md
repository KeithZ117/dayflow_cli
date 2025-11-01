````markdown
# Gemini Dayflow CLI - Activity Logger & Video Analyzer

这是一个智能活动跟踪工具，可以记录你的电脑使用情况、录制屏幕，并通过 Gemini AI 分析你的专注度和工作状态。

## 功能特性

- 🖥️ **活动监控**：自动记录活动窗口、应用程序和 URL
- 📹 **屏幕录制**：录制你的工作过程（含摄像头画中画）
- 🤖 **AI 分析**：使用 Gemini 2.5 Flash 分析视频，评估专注度和时间使用
- 📊 **数据导出**：生成 CSV 日志和结构化分析报告

## 项目结构

```
gemini_dayflow_cli/
├── main.py                    # 主入口：活动记录 + 录屏 + 自动分析
├── gemini_cli.py             # Gemini API CLI 工具（独立使用）
├── activity_log.csv          # 活动日志（自动生成）
├── requirements.txt
├── README.md
├── src/
│   ├── config.py             # 配置文件（FPS、输出路径等）
│   ├── core/                 # 核心功能模块
│   │   ├── activity.py       # 窗口活动监控
│   │   └── recorder.py       # 屏幕录制器
│   ├── utils/                # 工具函数
│   │   ├── analyze.py        # CSV 数据分析
│   │   └── file_handler.py   # 文件操作
│   └── api/                  # Gemini API 集成
│       ├── files.py          # Files API 核心功能
│       └── cli.py            # CLI 命令行接口
└── output/
    ├── dailylogs/            # AI 分析报告（.txt）
    └── videos/               # 录制的视频文件
```

## 安装

1.  克隆仓库：
    ```bash
    git clone <your-repo-url>
    cd gemini_dayflow_cli
    ```

2.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

3.  配置 API Key：
    创建 `.env` 文件：
    ```bash
    GOOGLE_API_KEY=your_gemini_api_key_here
    ```

## 使用方法

### 1. 主程序 - 活动跟踪 + 自动分析

运行主程序，开始记录活动并录屏：

```bash
python main.py
```

- 按 `Ctrl+C` 停止
- 自动生成：
  - `activity_log.csv` - 活动记录
  - `output/videos/dayflow_YYYY-MM-DD_HH-MM-SS.mp4` - 录制视频
  - `output/dailylogs/dayflow_YYYY-MM-DD_HH-MM-SS.txt` - AI 分析报告

### 2. CSV 数据分析

分析已有的活动日志：

```bash
python main.py analyze
```

### 3. Gemini API CLI 工具（独立使用）

#### 上传视频到 Gemini Files API：
```bash
python gemini_cli.py upload --file output/videos/my_video.mp4 --display-name "我的工作视频"
```

#### 列出所有已上传的文件：
```bash
python gemini_cli.py list
```

#### 获取文件元数据：
```bash
python gemini_cli.py get --name files/abc123xyz
```

#### 分析视频（自定义 Prompt）：
```bash
python gemini_cli.py analyze --name files/abc123xyz --prompt "请详细分析这个视频中的工作内容" --wait
```

**高级分析选项：**
```bash
# 分析视频片段（从 1 分钟到 5 分钟）
python gemini_cli.py analyze --name files/abc123xyz --start 01:00 --end 05:00 --wait

# 自定义采样率
python gemini_cli.py analyze --name files/abc123xyz --fps 0.5 --wait
```

## 配置

编辑 `src/config.py` 自定义设置：

```python
FPS = 1.0                    # 录屏帧率（帧/秒）
OUTPUT_DIR = "output"        # 输出目录
VIDEO_CODEC = "mp4v"        # 视频编码器
```

## 依赖项

- `opencv-python` - 屏幕录制
- `pywin32` - Windows 窗口监控
- `google-genai` - Gemini API 集成
- `pygetwindow` - 窗口管理
- `Pillow` - 图像处理
- `mss` - 屏幕截图

## 注意事项

- 本项目仅支持 Windows 系统
- 需要摄像头权限（用于专注度分析）
- 视频上传到 Gemini Files API 后会在云端保留 48 小时

## License

MIT

````
