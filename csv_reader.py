import pandas as pd
import os
import logging
from typing import List, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('csv_reader')

class CSVLinkReader:
    """
    从CSV文件中读取小宇宙播客链接
    """
    
    def __init__(self, csv_file_path: str):
        """
        初始化CSV链接读取器
        
        Args:
            csv_file_path: CSV文件的路径
        """
        self.csv_file_path = csv_file_path
        self.links = []
        logger.info(f"初始化CSV链接读取器，文件路径: {csv_file_path}")
        
    def read_links(self, column_name: Optional[str] = None) -> List[str]:
        """
        读取CSV文件中的链接
        
        Args:
            column_name: 包含链接的列名，如果为None，则尝试自动检测
            
        Returns:
            包含所有链接的列表
        """
        if not os.path.exists(self.csv_file_path):
            logger.error(f"CSV文件不存在: {self.csv_file_path}")
            raise FileNotFoundError(f"CSV文件不存在: {self.csv_file_path}")
        
        try:
            # 读取CSV文件
            df = pd.read_csv(self.csv_file_path)
            logger.info(f"成功读取CSV文件，共{len(df)}行")
            
            # 如果未指定列名，尝试自动检测包含链接的列
            if column_name is None:
                for col in df.columns:
                    # 检查第一个非空值是否包含小宇宙链接
                    first_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
                    if isinstance(first_value, str) and "xiaoyuzhoufm.com" in first_value:
                        column_name = col
                        logger.info(f"自动检测到链接列: {column_name}")
                        break
                
                if column_name is None:
                    logger.error("无法自动检测到包含小宇宙链接的列")
                    raise ValueError("无法自动检测到包含小宇宙链接的列，请指定column_name参数")
            
            # 提取链接
            links = df[column_name].dropna().tolist()
            
            # 验证链接格式
            valid_links = []
            for link in links:
                if isinstance(link, str) and "xiaoyuzhoufm.com/episode/" in link:
                    valid_links.append(link)
                else:
                    logger.warning(f"跳过无效链接: {link}")
            
            self.links = valid_links
            logger.info(f"成功提取{len(valid_links)}个有效链接")
            
            return valid_links
            
        except Exception as e:
            logger.error(f"读取CSV文件时出错: {str(e)}")
            raise
    
    def extract_episode_ids(self) -> List[str]:
        """
        从链接中提取剧集ID
        
        Returns:
            包含所有剧集ID的列表
        """
        if not self.links:
            logger.warning("链接列表为空，请先调用read_links方法")
            return []
        
        episode_ids = []
        for link in self.links:
            try:
                # 提取形如67f51aedf9578163d6d17090的ID
                if "/episode/" in link:
                    episode_id = link.split("/episode/")[1].split("?")[0]
                    episode_ids.append(episode_id)
                else:
                    logger.warning(f"无法从链接中提取剧集ID: {link}")
            except Exception as e:
                logger.error(f"提取剧集ID时出错: {str(e)}")
        
        logger.info(f"成功提取{len(episode_ids)}个剧集ID")
        return episode_ids

# 测试代码
if __name__ == "__main__":
    # 这部分代码仅在直接运行此文件时执行，用于测试
    import sys
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        reader = CSVLinkReader(csv_file)
        links = reader.read_links()
        episode_ids = reader.extract_episode_ids()
        
        print(f"找到 {len(links)} 个链接:")
        for i, link in enumerate(links[:5]):
            print(f"{i+1}. {link}")
        
        if len(links) > 5:
            print("...")
            
        print(f"\n提取的剧集ID:")
        for i, episode_id in enumerate(episode_ids[:5]):
            print(f"{i+1}. {episode_id}")
            
        if len(episode_ids) > 5:
            print("...")
    else:
        print("使用方法: python csv_reader.py <csv文件路径>")
