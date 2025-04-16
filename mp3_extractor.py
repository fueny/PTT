import os
import time
import logging
import re
import datetime
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import requests
from urllib.parse import urlparse, unquote

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mp3_extractor')

class MP3Extractor:
    """
    使用Selenium从小宇宙播客页面提取MP3文件
    """

    def __init__(self, output_dir: str):
        """
        初始化MP3提取器

        Args:
            output_dir: MP3文件保存目录
        """
        self.output_dir = output_dir
        self.driver = None
        logger.info(f"初始化MP3提取器，输出目录: {output_dir}")

        # 创建输出目录（如果不存在）
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出目录: {output_dir}")

    def setup_driver(self):
        """
        设置Selenium WebDriver
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 无头模式
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # 设置下载偏好（虽然我们不会直接下载，但这可能有助于检测下载链接）
            chrome_options.add_experimental_option(
                "prefs", {
                    "download.default_directory": self.output_dir,
                    "download.prompt_for_download": False,
                }
            )

            try:
                # 尝试直接初始化Chrome，不使用ChromeDriverManager
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("成功设置WebDriver（直接初始化）")
            except Exception as inner_e:
                logger.warning(f"直接初始化WebDriver失败，尝试使用ChromeDriverManager: {str(inner_e)}")
                # 使用webdriver_manager自动下载和管理ChromeDriver
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("成功设置WebDriver（使用ChromeDriverManager）")

        except Exception as e:
            logger.error(f"设置WebDriver时出错: {str(e)}")
            raise

    def extract_mp3_from_episode(self, episode_url: str) -> Optional[str]:
        """
        从小宇宙播客剧集页面提取MP3文件

        Args:
            episode_url: 小宇宙播客剧集URL

        Returns:
            保存的MP3文件路径，如果提取失败则返回None
        """
        if self.driver is None:
            self.setup_driver()

        try:
            # 提取剧集ID
            episode_id = None
            if "/episode/" in episode_url:
                episode_id = episode_url.split("/episode/")[1].split("?")[0]

            if not episode_id:
                logger.error(f"无法从URL提取剧集ID: {episode_url}")
                return None

            logger.info(f"正在处理剧集: {episode_id}")

            # 访问页面
            logger.info(f"正在访问页面: {episode_url}")
            self.driver.get(episode_url)

            # 等待页面加载
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "audio"))
            )

            # 获取页面标题作为文件名的一部分
            try:
                title_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title"))
                )
                title = title_element.text
                # 清理标题，移除不适合作为文件名的字符
                title = re.sub(r'[\\/*?:"<>|]', "", title)
                title = title[:50] if len(title) > 50 else title  # 限制长度
            except Exception as e:
                logger.warning(f"无法获取标题，将使用剧集ID作为文件名: {str(e)}")
                title = episode_id

            # 查找音频元素
            audio_element = self.driver.find_element(By.TAG_NAME, "audio")
            mp3_url = audio_element.get_attribute("src")

            if not mp3_url:
                logger.warning("未找到直接的音频URL，尝试其他方法...")

                # 尝试通过网络请求查找
                audio_urls = self.extract_audio_urls_from_network()
                if audio_urls:
                    mp3_url = audio_urls[0]
                    logger.info(f"通过网络请求找到音频URL: {mp3_url}")
                else:
                    logger.error("无法找到音频URL")
                    return None

            # 生成时间戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            # 创建文件名
            filename = f"{episode_id}_{timestamp}.mp3"
            filepath = os.path.join(self.output_dir, filename)

            # 下载MP3文件
            logger.info(f"正在下载MP3文件: {mp3_url}")
            self.download_file(mp3_url, filepath)

            logger.info(f"成功下载MP3文件: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"提取MP3文件时出错: {str(e)}")
            return None

    def extract_audio_urls_from_network(self) -> list:
        """
        从网络请求中提取音频URL

        Returns:
            包含音频URL的列表
        """
        try:
            # 执行JavaScript获取网络请求
            logs = self.driver.execute_script("""
                var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
                var network = performance.getEntries() || [];
                return network;
            """)

            # 筛选可能的音频URL
            audio_urls = []
            for log in logs:
                if 'name' in log and isinstance(log['name'], str):
                    url = log['name']
                    if url.endswith('.mp3') or '.mp3?' in url or 'audio' in url.lower():
                        audio_urls.append(url)

            return audio_urls

        except Exception as e:
            logger.error(f"从网络请求中提取音频URL时出错: {str(e)}")
            return []

    def download_file(self, url: str, filepath: str):
        """
        下载文件

        Args:
            url: 文件URL
            filepath: 保存路径
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        except Exception as e:
            logger.error(f"下载文件时出错: {str(e)}")
            raise

    def process_episode_batch(self, episode_urls: list) -> list:
        """
        批量处理多个剧集

        Args:
            episode_urls: 剧集URL列表

        Returns:
            包含成功下载的MP3文件路径的列表
        """
        if self.driver is None:
            self.setup_driver()

        downloaded_files = []

        for url in episode_urls:
            try:
                filepath = self.extract_mp3_from_episode(url)
                if filepath:
                    downloaded_files.append(filepath)
                # 添加短暂延迟，避免请求过于频繁
                time.sleep(2)
            except Exception as e:
                logger.error(f"处理剧集时出错: {url}, 错误: {str(e)}")

        return downloaded_files

    def close(self):
        """
        关闭WebDriver
        """
        if self.driver:
            self.driver.quit()
            logger.info("已关闭WebDriver")

# 测试代码
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        episode_url = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "./mp3_files"

        extractor = MP3Extractor(output_dir)
        try:
            filepath = extractor.extract_mp3_from_episode(episode_url)
            if filepath:
                print(f"成功下载MP3文件: {filepath}")
            else:
                print("下载失败")
        finally:
            extractor.close()
    else:
        print("使用方法: python mp3_extractor.py <小宇宙剧集URL> [输出目录]")
