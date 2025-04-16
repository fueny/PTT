#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本 - 验证小宇宙博客音频转录自动化流程
"""

import os
import sys
import logging
import argparse
from csv_reader import CSVLinkReader

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test')

def test_csv_reader(csv_file):
    """测试CSV链接读取功能"""
    logger.info("测试CSV链接读取功能...")
    try:
        reader = CSVLinkReader(csv_file)
        links = reader.read_links()
        episode_ids = reader.extract_episode_ids()
        
        logger.info(f"成功读取 {len(links)} 个链接")
        for i, link in enumerate(links):
            logger.info(f"链接 {i+1}: {link}")
        
        logger.info(f"成功提取 {len(episode_ids)} 个剧集ID")
        for i, episode_id in enumerate(episode_ids):
            logger.info(f"剧集ID {i+1}: {episode_id}")
        
        return True
    except Exception as e:
        logger.error(f"CSV链接读取测试失败: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="测试小宇宙博客音频转录自动化流程")
    parser.add_argument("csv_file", help="包含小宇宙播客链接的CSV文件路径")
    
    args = parser.parse_args()
    
    # 测试CSV链接读取功能
    if test_csv_reader(args.csv_file):
        logger.info("CSV链接读取测试通过")
    else:
        logger.error("CSV链接读取测试失败")
        sys.exit(1)
    
    logger.info("所有测试通过")

if __name__ == "__main__":
    main()
