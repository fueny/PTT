import os
import logging
import tempfile
import time
import sys
from typing import List, Optional, Dict, Any, Tuple

# 添加ffmpeg到系统路径
ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg_bin', 'ffmpeg-master-latest-win64-gpl', 'bin')
os.environ['PATH'] = ffmpeg_path + os.pathsep + os.environ['PATH']

from pydub import AudioSegment
from pydub.silence import split_on_silence
import whisper
import torch
import numpy as np
from tqdm import tqdm

# 导入繁体转简体的库
import opencc

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('whisper_transcriber')

class WhisperTranscriber:
    """
    使用Whisper模型进行中文音频转录
    """

    def __init__(self, model_size: str = "small", device: str = None, to_simplified: bool = True):
        """
        初始化Whisper转录器

        Args:
            model_size: Whisper模型大小，可选值为"tiny", "base", "small", "medium", "large"
            device: 运行设备，可以是"cpu"或"cuda"，如果为None则自动检测
            to_simplified: 是否将繁体中文转换为简体中文
        """
        self.model_size = model_size
        self.to_simplified = to_simplified

        # 初始化繁简转换器
        if self.to_simplified:
            self.converter = opencc.OpenCC('t2s')  # 繁体到简体

        # 自动检测设备
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model = None
        logger.info(f"初始化Whisper转录器，模型大小: {model_size}，设备: {self.device}，繁转简: {to_simplified}")

    def convert_to_simplified(self, text: str) -> str:
        """
        将繁体中文转换为简体中文

        Args:
            text: 要转换的繁体中文文本

        Returns:
            转换后的简体中文文本
        """
        if self.to_simplified:
            return self.converter.convert(text)
        return text

    def load_model(self):
        """
        加载Whisper模型
        """
        try:
            start_time = time.time()
            logger.info(f"正在加载Whisper模型 ({self.model_size})...")

            # 加载模型
            self.model = whisper.load_model(self.model_size, device=self.device)

            end_time = time.time()
            logger.info(f"成功加载Whisper模型，耗时: {end_time - start_time:.2f}秒")

        except Exception as e:
            logger.error(f"加载Whisper模型时出错: {str(e)}")
            raise

    def transcribe_audio(self, audio_path: str, language: str = "zh") -> Dict[str, Any]:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径
            language: 音频语言，默认为中文 (zh)

        Returns:
            包含转录结果的字典
        """
        if self.model is None:
            self.load_model()

        try:
            logger.info(f"正在转录音频文件: {audio_path}")

            # 转录音频
            result = self.model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                verbose=False
            )

            # 如果需要，将繁体中文转换为简体中文
            if self.to_simplified and language == "zh":
                # 转换完整文本
                result["text"] = self.convert_to_simplified(result["text"])

                # 转换每个片段的文本
                for segment in result["segments"]:
                    segment["text"] = self.convert_to_simplified(segment["text"])

                logger.info("已将转录结果从繁体中文转换为简体中文")

            logger.info(f"成功转录音频文件: {audio_path}")
            return result

        except Exception as e:
            logger.error(f"转录音频文件时出错: {str(e)}")
            raise

    def split_audio(self, audio_path: str, output_dir: str,
                   chunk_length_ms: int = 10 * 60 * 1000,  # 默认10分钟
                   min_silence_len: int = 1000,  # 1秒
                   silence_thresh: int = -40,  # 静音阈值
                   keep_silence: int = 500  # 保留500毫秒的静音
                  ) -> List[str]:
        """
        将长音频分割成多个小片段

        Args:
            audio_path: 音频文件路径
            output_dir: 输出目录
            chunk_length_ms: 每个片段的最大长度（毫秒）
            min_silence_len: 最小静音长度（毫秒）
            silence_thresh: 静音阈值（dB）
            keep_silence: 保留的静音长度（毫秒）

        Returns:
            包含所有分割后音频文件路径的列表
        """
        try:
            # 确保输出目录存在
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 获取文件名（不含扩展名）
            base_name = os.path.splitext(os.path.basename(audio_path))[0]

            logger.info(f"正在加载音频文件: {audio_path}")
            audio = AudioSegment.from_file(audio_path)

            # 获取音频总长度（毫秒）
            total_length_ms = len(audio)
            logger.info(f"音频总长度: {total_length_ms/1000/60:.2f}分钟")

            # 如果音频长度小于指定的片段长度，直接返回原文件
            if total_length_ms <= chunk_length_ms:
                logger.info(f"音频长度小于指定的片段长度，无需分割")
                return [audio_path]

            # 尝试在静音处分割
            logger.info(f"正在按静音分割音频...")
            chunks = split_on_silence(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh,
                keep_silence=keep_silence
            )

            # 如果没有找到足够的静音点，或者分割后的片段仍然太长，则按固定长度分割
            if not chunks or max(len(chunk) for chunk in chunks) > chunk_length_ms:
                logger.info(f"按静音分割不理想，改为按固定长度分割...")
                chunks = [audio[i:i+chunk_length_ms] for i in range(0, total_length_ms, chunk_length_ms)]

            # 保存分割后的音频文件
            chunk_files = []
            for i, chunk in enumerate(chunks):
                chunk_path = os.path.join(output_dir, f"{base_name}_{i+1:03d}.mp3")
                logger.info(f"正在保存音频片段 {i+1}/{len(chunks)}: {chunk_path}")
                chunk.export(chunk_path, format="mp3")
                chunk_files.append(chunk_path)

            logger.info(f"成功将音频分割为 {len(chunk_files)} 个片段")
            return chunk_files

        except Exception as e:
            logger.error(f"分割音频文件时出错: {str(e)}")
            raise

    def transcribe_long_audio(self, audio_path: str, output_dir: Optional[str] = None,
                             language: str = "zh") -> Dict[str, Any]:
        """
        转录长音频文件，自动分割处理

        Args:
            audio_path: 音频文件路径
            output_dir: 分割音频的输出目录，如果为None则使用临时目录
            language: 音频语言，默认为中文 (zh)

        Returns:
            包含合并后转录结果的字典
        """
        if self.model is None:
            self.load_model()

        try:
            # 如果未指定输出目录，则创建临时目录
            if output_dir is None:
                # 创建与音频文件同名的目录
                base_name = os.path.splitext(os.path.basename(audio_path))[0]
                parent_dir = os.path.dirname(audio_path)
                output_dir = os.path.join(parent_dir, base_name)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                logger.info(f"创建音频分割输出目录: {output_dir}")

            # 分割音频
            chunk_files = self.split_audio(audio_path, output_dir)

            # 如果只有一个片段，直接转录
            if len(chunk_files) == 1 and chunk_files[0] == audio_path:
                return self.transcribe_audio(audio_path, language)

            # 转录每个片段
            all_segments = []
            total_duration = 0.0

            for i, chunk_path in enumerate(chunk_files):
                logger.info(f"正在转录片段 {i+1}/{len(chunk_files)}: {chunk_path}")
                try:
                    result = self.transcribe_audio(chunk_path, language)

                    # 将单个片段的转录结果保存为MD文件（便于调试和备份）
                    chunk_md_path = os.path.splitext(chunk_path)[0] + '.md'
                    self.save_transcript_to_markdown(result, chunk_md_path)
                    logger.info(f"已保存片段 {i+1} 的转录结果到: {chunk_md_path}")

                    # 调整时间戳
                    for segment in result["segments"]:
                        segment["start"] += total_duration
                        segment["end"] += total_duration

                    all_segments.extend(result["segments"])
                    total_duration += result["segments"][-1]["end"] if result["segments"] else 0

                except Exception as e:
                    logger.error(f"转录片段 {i+1} 时出错: {str(e)}")
                    # 继续处理下一个片段，而不是中断整个过程

            # 合并结果
            merged_result = {
                "text": " ".join(segment["text"] for segment in all_segments),
                "segments": all_segments,
                "language": language
            }

            logger.info(f"成功转录长音频文件: {audio_path}")
            return merged_result

        except Exception as e:
            logger.error(f"转录长音频文件时出错: {str(e)}")
            raise

    def save_transcript_to_markdown(self, transcript: Dict[str, Any], output_path: str):
        """
        将转录结果保存为Markdown文件

        Args:
            transcript: 转录结果
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入标题
                f.write("# 音频转录\n\n")

                # 写入音频信息
                f.write("## 音频信息\n\n")
                f.write(f"- 语言: {transcript.get('language', '未知')}\n")
                if 'segments' in transcript and transcript['segments']:
                    # 限制时间戳的最大值以避免异常大的时间
                    max_time = 10 * 3600  # 10小时为上限
                    duration = min(transcript['segments'][-1]['end'], max_time)

                    # 格式化时长显示
                    hours = int(duration / 3600)
                    minutes = int((duration % 3600) / 60)
                    seconds = int(duration % 60)

                    if hours > 0:
                        duration_str = f"{hours}小时{minutes}分钟{seconds}秒"
                    else:
                        duration_str = f"{minutes}分钟{seconds}秒"

                    f.write(f"- 时长: {duration_str}\n")
                f.write("\n")

                # 写入完整转录文本
                f.write("## 完整转录文本\n\n")
                f.write(transcript.get('text', '').strip())
                f.write("\n\n")

                # 写入带时间戳的分段文本
                if 'segments' in transcript and transcript['segments']:
                    f.write("## 带时间戳的分段文本\n\n")
                    for segment in transcript['segments']:
                        start_time = segment['start']
                        end_time = segment['end']
                        text = segment['text'].strip()

                        # 格式化时间戳为 [时:分:秒] 或 [分:秒]
                        # 限制时间戳的最大值以避免异常大的时间
                        max_time = 10 * 3600  # 10小时为上限
                        start_time = min(start_time, max_time)
                        end_time = min(end_time, max_time)

                        if start_time >= 3600 or end_time >= 3600:  # 如果超过1小时
                            start_hours = int(start_time / 3600)
                            start_minutes = int((start_time % 3600) / 60)
                            start_seconds = int(start_time % 60)
                            start_formatted = f"{start_hours:02d}:{start_minutes:02d}:{start_seconds:02d}"

                            end_hours = int(end_time / 3600)
                            end_minutes = int((end_time % 3600) / 60)
                            end_seconds = int(end_time % 60)
                            end_formatted = f"{end_hours:02d}:{end_minutes:02d}:{end_seconds:02d}"
                        else:  # 不到1小时
                            start_formatted = f"{int(start_time/60):02d}:{int(start_time%60):02d}"
                            end_formatted = f"{int(end_time/60):02d}:{int(end_time%60):02d}"

                        f.write(f"**[{start_formatted}-{end_formatted}]** {text}\n\n")

            logger.info(f"成功将转录结果保存为Markdown文件: {output_path}")

        except Exception as e:
            logger.error(f"保存转录结果时出错: {str(e)}")
            raise

# 测试代码
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        model_size = sys.argv[2] if len(sys.argv) > 2 else "small"

        transcriber = WhisperTranscriber(model_size=model_size)

        # 获取音频文件名（不含扩展名）
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        parent_dir = os.path.dirname(audio_path)

        # 创建输出目录
        output_dir = os.path.join(parent_dir, base_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 转录音频
        transcript = transcriber.transcribe_long_audio(audio_path, output_dir=output_dir)

        # 保存转录结果
        output_path = os.path.join(parent_dir, f"{base_name}.md")
        transcriber.save_transcript_to_markdown(transcript, output_path)

        print(f"转录完成，结果已保存至: {output_path}")
    else:
        print("使用方法: python whisper_transcriber.py <音频文件路径> [模型大小]")
        print("模型大小可选值: tiny, base, small, medium, large (默认为small)")
