#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
小宇宙博客音频转录自动化流程
主工作流程脚本
"""

import os
import sys
import logging
import argparse
import time
import datetime
from typing import List, Optional, Dict, Any

# 导入自定义模块
from csv_reader import CSVLinkReader
from mp3_extractor import MP3Extractor
from whisper_transcriber import WhisperTranscriber

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("podcast_transcriber.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('main')

def create_directory_structure(base_dir: str) -> Dict[str, str]:
    """
    创建项目目录结构

    Args:
        base_dir: 基础目录路径

    Returns:
        包含各个目录路径的字典
    """
    dirs = {
        "mp3": os.path.join(base_dir, "mp3_files"),
        "transcripts": os.path.join(base_dir, "transcripts"),
        "temp": os.path.join(base_dir, "temp")
    }

    for name, path in dirs.items():
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"创建目录: {path}")

    return dirs

def process_podcast_links(csv_file: str, output_base_dir: str,
                         whisper_model_size: str = "small",
                         column_name: Optional[str] = None,
                         to_simplified: bool = True) -> None:
    """
    处理播客链接的主工作流程

    Args:
        csv_file: CSV文件路径
        output_base_dir: 输出基础目录
        whisper_model_size: Whisper模型大小
        column_name: CSV中包含链接的列名
        to_simplified: 是否将繁体中文转换为简体中文
    """
    try:
        # 创建目录结构
        dirs = create_directory_structure(output_base_dir)

        # 步骤1: 读取CSV文件中的链接
        logger.info("步骤1: 读取CSV文件中的链接")
        csv_reader = CSVLinkReader(csv_file)
        links = csv_reader.read_links(column_name)
        episode_ids = csv_reader.extract_episode_ids()

        logger.info(f"从CSV文件中读取了 {len(links)} 个链接")

        # 初始化MP3提取器和Whisper转录器
        mp3_extractor = MP3Extractor(dirs["mp3"])
        transcriber = WhisperTranscriber(model_size=whisper_model_size, to_simplified=to_simplified)

        # 加载Whisper模型（提前加载以节省时间）
        transcriber.load_model()

        # 处理每个播客链接
        for i, (link, episode_id) in enumerate(zip(links, episode_ids)):
            try:
                logger.info(f"正在处理第 {i+1}/{len(links)} 个播客: {link}")

                # 步骤2: 提取MP3文件
                logger.info(f"步骤2: 提取MP3文件")
                mp3_path = mp3_extractor.extract_mp3_from_episode(link)

                if not mp3_path:
                    logger.error(f"无法提取MP3文件，跳过此播客: {link}")
                    continue

                # 创建音频分割的输出目录
                audio_chunks_dir = os.path.join(dirs["mp3"], episode_id)
                if not os.path.exists(audio_chunks_dir):
                    os.makedirs(audio_chunks_dir)

                # 步骤3: 使用Whisper进行音频转录
                logger.info(f"步骤3: 使用Whisper进行音频转录")
                transcript = transcriber.transcribe_long_audio(
                    mp3_path,
                    output_dir=audio_chunks_dir,
                    language="zh"
                )

                # 步骤4: 生成Markdown文档
                logger.info(f"步骤4: 生成Markdown文档")
                # 创建对应的transcripts子文件夹
                episode_transcript_dir = os.path.join(dirs["transcripts"], episode_id)
                if not os.path.exists(episode_transcript_dir):
                    os.makedirs(episode_transcript_dir)
                    logger.info(f"创建转录文件输出目录: {episode_transcript_dir}")

                # 使用episode_id作为文件名
                md_path = os.path.join(episode_transcript_dir, f"{episode_id}.md")
                transcriber.save_transcript_to_markdown(transcript, md_path)

                logger.info(f"成功处理播客: {link}")
                logger.info(f"MP3文件: {mp3_path}")
                logger.info(f"Markdown文档: {md_path}")

                # 短暂延迟，避免请求过于频繁
                time.sleep(2)

            except Exception as e:
                logger.error(f"处理播客时出错: {link}, 错误: {str(e)}")

        # 关闭MP3提取器
        mp3_extractor.close()

        logger.info("所有播客处理完成")

    except Exception as e:
        logger.error(f"工作流程执行时出错: {str(e)}")
        raise

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description="小宇宙博客音频转录自动化流程")
    parser.add_argument("csv_file", help="包含小宇宙播客链接的CSV文件路径")
    parser.add_argument("--output-dir", "-o", default="./output", help="输出目录路径")
    parser.add_argument("--model-size", "-m", default="small",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper模型大小")
    parser.add_argument("--column-name", "-c", help="CSV中包含链接的列名")
    parser.add_argument("--simplified", "-s", action="store_true", default=True,
                        help="将繁体中文转换为简体中文（默认启用）")
    parser.add_argument("--traditional", "-t", action="store_false", dest="simplified",
                        help="保持繁体中文不转换")

    args = parser.parse_args()

    # 记录开始时间
    start_time = time.time()

    # 执行工作流程
    process_podcast_links(
        args.csv_file,
        args.output_dir,
        args.model_size,
        args.column_name,
        args.simplified
    )

    # 记录结束时间
    end_time = time.time()
    elapsed_time = end_time - start_time

    # 格式化耗时
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    logger.info(f"工作流程完成，总耗时: {int(hours)}小时 {int(minutes)}分钟 {seconds:.2f}秒")

if __name__ == "__main__":
    main()
