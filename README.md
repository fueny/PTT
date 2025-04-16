# 小宇宙博客音频转录自动化流程

这是一个自动化工具，用于批量从小宇宙博客下载音频并转录为文本。该工具可以：

1. 从CSV文件批量读取小宇宙博客链接
2. 使用Selenium自动提取页面中的MP3文件
3. 使用Whisper开源模型进行中文语音转文字
4. 生成结构化Markdown文档

## 系统要求

- Python 3.10+
- ffmpeg
- Chrome浏览器（用于Selenium）
- 足够的磁盘空间用于存储音频文件和转录结果

## 安装

1. 克隆或下载本项目到本地

2. 运行安装脚本安装依赖：

```bash
chmod +x setup.sh
./setup.sh
```

或者手动安装依赖：

```bash
# 安装ffmpeg
sudo apt-get update && sudo apt-get install -y ffmpeg

# 安装Python依赖
pip3 install -r requirements.txt
```

## 使用方法

### 准备CSV文件

创建一个包含小宇宙播客链接的CSV文件，格式如下：

```
url
https://www.xiaoyuzhoufm.com/episode/67f51aedf9578163d6d17090
```

CSV文件应至少包含一列，其中包含形如`https://www.xiaoyuzhoufm.com/episode/[ID]`的链接。

### 运行主程序

```bash
python main.py your_links.csv [options]
```

#### 必需参数

- `your_links.csv`：包含小宇宙播客链接的CSV文件路径

#### 可选参数

- `--output-dir`, `-o`：输出目录路径，默认为 `./output`
- `--model-size`, `-m`：Whisper模型大小，可选值为 `tiny`, `base`, `small`, `medium`, `large`，默认为 `small`
- `--column-name`, `-c`：CSV文件中包含链接的列名。如果不指定，程序将自动尝试识别包含链接的列
- `--simplified`, `-s`：将繁体中文转换为简体中文（默认启用）
- `--traditional`, `-t`：保持繁体中文不转换

#### 示例

1. 使用默认参数：

```bash
python main.py sample_links.csv
```

2. 指定输出目录和模型大小：

```bash
python main.py sample_links.csv --output-dir ./my_output --model-size medium
```

3. 指定CSV文件中的链接列名：

```bash
python main.py sample_links.csv --column-name podcast_url
```

4. 保持繁体中文不转换：

```bash
python main.py sample_links.csv --traditional
```

### 输出结构

程序会在指定的输出目录中创建以下子目录：

- `mp3_files`：存放下载的MP3文件
  - `[episode_id]`：每个播客的音频片段目录
    - `[episode_id]_[timestamp]_001.mp3`：分割后的音频片段
    - `[episode_id]_[timestamp]_001.md`：单个片段的转录结果
    - ...
- `transcripts`：存放生成的Markdown转录文件
  - `[episode_id]`：每个播客的转录结果目录
    - `[episode_id].md`：完整的转录文档
- `temp`：存放临时文件

对于长音频，程序会自动分割成多个小片段，每个片段都会被单独转录，并将结果保存在对应的目录中。

## 模块说明

本项目包含以下主要模块：

1. `csv_reader.py`：从CSV文件读取小宇宙播客链接
2. `mp3_extractor.py`：使用Selenium从小宇宙播客页面提取MP3文件
3. `whisper_transcriber.py`：使用Whisper模型进行中文音频转录
4. `main.py`：整合所有组件的主工作流程

## 注意事项

1. **磁盘空间**：Whisper模型和音频文件可能占用大量磁盘空间，请确保有足够的存储空间。

2. **模型选择**：
   - `tiny`和`base`模型较小，但准确度较低
   - `small`模型是大小和准确度的良好平衡
   - `medium`和`large`模型准确度最高，但需要更多计算资源和磁盘空间

3. **长音频处理**：对于长播客（超过10分钟），程序会自动分割音频并分段处理，然后合并结果。每个音频片段都会生成单独的转录文件，并保存在相应的目录中。

4. **中文支持**：本工具专为中文播客优化，使用Whisper模型的中文语言设置。默认将繁体中文转换为简体中文，可使用 `--traditional` 参数保持繁体中文。

5. **ffmpeg依赖**：程序依赖ffmpeg进行音频处理，请确保系统中已安装并添加到系统路径中。

## 故障排除

1. **Selenium错误**：
   - 确保已安装Chrome浏览器
   - 检查网络连接是否正常
   - 尝试增加等待时间
   - 如果出现WebDriver错误，可能需要更新Chrome浏览器或ChromeDriver

2. **ffmpeg相关问题**：
   - 如果出现“ffmpeg not found”错误，请确保系统中已安装ffmpeg并添加到系统路径中
   - 可以使用命令行运行 `ffmpeg -version` 来验证ffmpeg是否正确安装

3. **Whisper模型问题**：
   - 如果遇到磁盘空间不足，尝试使用较小的模型（如`tiny`或`base`）
   - 清理临时文件和缓存：`pip cache purge`
   - 如果转录质量不佳，尝试使用更大的模型（如`medium`或`large`）

4. **音频提取失败**：
   - 检查小宇宙链接是否有效
   - 小宇宙网站结构可能发生变化，可能需要更新提取逻辑

5. **转录结果不完整**：
   - 如果只有部分音频片段被转录，可以尝试运行 `test_transcribe_all.py` 脚本来单独转录所有片段
   - 命令示例：`python test_transcribe_all.py ./output/mp3_files/[episode_id] ./output/transcripts/[episode_id] small`

## 测试

### 基本测试

运行测试脚本验证CSV读取功能：

```bash
python test.py sample_links.csv
```

### 音频片段转录测试

如果需要单独转录所有音频片段，可以使用以下命令：

```bash
python test_transcribe_all.py <音频片段目录> <输出目录> [model-size] [--traditional]
```

示例：

```bash
python test_transcribe_all.py ./output/mp3_files/67f51aedf9578163d6d17090 ./output/transcripts/67f51aedf9578163d6d17090 small
```

保持繁体中文不转换：

```bash
python test_transcribe_all.py ./output/mp3_files/67f51aedf9578163d6d17090 ./output/transcripts/67f51aedf9578163d6d17090 small --traditional
```

## 许可证

本项目采用MIT许可证。

## 作者

[您的名称]

## 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 用于语音识别的开源模型
- [Selenium](https://www.selenium.dev/) - 用于网页自动化
- [小宇宙](https://www.xiaoyuzhoufm.com/) - 播客平台
