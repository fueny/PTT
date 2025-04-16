import os
import logging
import sys
from whisper_transcriber import WhisperTranscriber

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """
    测试转录所有音频片段
    """
    if len(sys.argv) < 3:
        print("使用方法: python test_transcribe_all.py <音频片段目录> <输出目录> [模型大小] [--traditional]")
        print("模型大小可选值: tiny, base, small, medium, large (默认为small)")
        print("--traditional: 保持繁体中文不转换（默认转换为简体中文）")
        return

    audio_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # 解析参数
    model_size = "small"
    to_simplified = True

    for i in range(3, len(sys.argv)):
        if sys.argv[i] in ["tiny", "base", "small", "medium", "large"]:
            model_size = sys.argv[i]
        elif sys.argv[i] == "--traditional":
            to_simplified = False

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 初始化转录器
    transcriber = WhisperTranscriber(model_size=model_size, to_simplified=to_simplified)
    logger.info(f"初始化转录器，模型大小: {model_size}, 繁转简: {to_simplified}")

    # 获取所有MP3文件
    mp3_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
    logger.info(f"找到 {len(mp3_files)} 个MP3文件")

    # 转录每个文件
    for i, mp3_file in enumerate(mp3_files):
        mp3_path = os.path.join(audio_dir, mp3_file)
        logger.info(f"正在处理第 {i+1}/{len(mp3_files)} 个文件: {mp3_file}")

        try:
            # 转录音频
            transcript = transcriber.transcribe_audio(mp3_path, language="zh")

            # 保存转录结果
            base_name = os.path.splitext(mp3_file)[0]
            md_path = os.path.join(output_dir, f"{base_name}.md")
            transcriber.save_transcript_to_markdown(transcript, md_path)

            logger.info(f"成功转录文件: {mp3_file}")
            logger.info(f"转录结果已保存至: {md_path}")

        except Exception as e:
            logger.error(f"转录文件时出错: {mp3_file}, 错误: {str(e)}")

    logger.info("所有文件处理完成")

if __name__ == "__main__":
    main()
