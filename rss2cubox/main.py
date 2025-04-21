import time
import feedparser
import requests
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from config import *

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rss2cubox.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def read_last_time() -> time.struct_time:
    """
    读取上次运行时间
    :return: 上次运行时间的时间结构
    """
    try:
        with open('timestramp.txt', 'r', encoding='utf-8') as log_file:
            log_list = log_file.readlines()
            if not log_list:
                logger.info(f"日志记录为空，使用配置的默认时间: {START_TIME}")
                return time.strptime(START_TIME, '%Y-%m-%d %H:%M:%S')
            
            last_line = log_list[-1].strip()
            return time.strptime(last_line, '%Y-%m-%d %H:%M:%S')
    except FileNotFoundError:
        logger.info(f"日志文件不存在，使用配置的默认时间: {START_TIME}")
    except ValueError as e:
        logger.error(f"解析日志时间出错: {e}")
    except Exception as e:
        logger.error(f"读取日志时发生未知错误: {e}")
    
    # 所有异常情况都返回配置中的默认时间
    return time.strptime(START_TIME, '%Y-%m-%d %H:%M:%S')


def write_time_log() -> None:
    """写入当前时间到日志"""
    now_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    try:
        with open('timestramp.txt', 'a', encoding='utf-8') as log_file:
            log_file.write(now_time + '\n')
        logger.info(f"更新日志时间: {now_time}")
    except Exception as e:
        logger.error(f"写入日志时出错: {e}")


def get_entry_time(entry: Dict[str, Any]) -> time.struct_time:
    """获取RSS条目的时间，按优先级尝试不同字段"""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return entry.published_parsed
    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return entry.updated_parsed
    elif hasattr(entry, 'created_parsed') and entry.created_parsed:
        return entry.created_parsed
    return time.localtime()  # 默认使用当前时间


def send_to_cubox(api: str, data: Dict[str, Any]) -> bool:
    """发送数据到Cubox API"""
    try:
        response = requests.post(api, json=data, timeout=10)
        result = response.json()
        
        if result.get('code') != 200 or result.get('message'):
            logger.error(f"API返回错误: {result}")
            return False
        
        return True
    except requests.RequestException as e:
        logger.error(f"发送请求失败: {e}")
        return False
    except Exception as e:
        logger.error(f"发送过程中出错: {e}")
        return False


def process_feed_entry(api: str, entry: Dict[str, Any], cubox_tags: List[str], 
                      cubox_folder: str, last_time: time.struct_time) -> Tuple[bool, Optional[str]]:
    """处理单个RSS条目"""
    try:
        entry_time = get_entry_time(entry)
        
        # 跳过旧文章
        if entry_time < last_time:
            return True, None
            
        article_url = entry.link
        article_title = entry.title
        article_description = entry.description if hasattr(entry, 'description') else ""
        
        data = {
            'type': 'url',
            'content': article_url,
            'title': article_title,
            'description': article_description,
            'tags': cubox_tags,
            'folder': cubox_folder
        }
        
        success = send_to_cubox(api, data)
        if success:
            return True, article_title
        return False, article_title
        
    except Exception as e:
        logger.error(f"处理条目时出错: {str(e)}")
        return False, None


def feed2cubox(api: str, feed_url: str, cubox_tags: List[str], cubox_folder: str, 
              last_time: time.struct_time) -> Optional[bool]:
    """
    处理单个RSS源，发送文章到Cubox
    
    :return: True-成功处理所有条目, False-处理失败, None-没有新内容
    """
    try:
        logger.info(f"开始处理RSS源: {feed_url}")
        # 添加超时设置，feedparser没有直接的timeout参数，需要通过requests获取内容
        try:
            response = requests.get(feed_url, timeout=10)
            feed = feedparser.parse(response.content)
        except requests.Timeout:
            logger.error(f"获取RSS源超时: {feed_url}")
            return False
        except requests.RequestException as e:
            logger.error(f"获取RSS源失败: {feed_url} - {e}")
            return False
        
        if hasattr(feed, 'bozo_exception'):
            logger.warning(f"RSS解析警告: {feed.bozo_exception}")
        
        if not feed.entries:
            logger.info(f"RSS源无条目: {feed_url}")
            return None
        
        # 安全获取更新时间
        if hasattr(feed, 'updated_parsed') and feed.updated_parsed:
            update_time = feed.updated_parsed
        elif feed.entries and hasattr(feed.entries[0], 'published_parsed') and feed.entries[0].published_parsed:
            update_time = feed.entries[0].published_parsed
        else:
            update_time = time.localtime()
        
        # 检查是否有更新
        if last_time > update_time:
            logger.info(f"RSS源无新内容: {feed_url}")
            return None
        
        # 处理所有条目
        success_count = 0
        for entry in feed.entries:
            success, title = process_feed_entry(api, entry, cubox_tags, cubox_folder, last_time)
            if not success and title:
                logger.error(f"发送失败: {title}")
                return False
            elif success and title:
                logger.info(f"成功发送: {title}")
                success_count += 1
        
        logger.info(f"RSS源 {feed_url} 处理完成, 成功发送 {success_count} 个条目")
        return True if success_count > 0 else None
        
    except Exception as e:
        logger.error(f"处理RSS源 {feed_url} 出错: {e}")
        traceback.print_exc()
        return False


def rss2cubox() -> bool:
    """
    主程序: 处理所有RSS源
    :return: 是否成功完成
    """
    start_time = datetime.now()
    logger.info("开始RSS转发任务")
    logger.info("-" * 50)
    
    try:
        # 优先从环境变量获取CUBOX_API，如果不存在则使用配置文件的值
        import os
        cubox_api = os.environ.get('CUBOX_API')
        if cubox_api:
            logger.info(f"从环境变量获取CUBOX_API: {cubox_api}")
        else:
            cubox_api = CUBOX_API
            logger.info(f"从配置文件获取CUBOX_API: {cubox_api}")
            
        cubox_tags = CUBOX_TAGS if CUBOX_TAGS else []
        cubox_folder = CUBOX_FOLDER
        feed_list = FEED_LIST
        
        # 读取上次运行时间
        last_time = read_last_time()
        logger.info(f"上次运行时间: {time.strftime('%Y-%m-%d %H:%M:%S', last_time)}")
        
        # 处理所有RSS源
        all_completed = True
        any_success = False
        
        # 使用线程池并行处理多个RSS源
        with ThreadPoolExecutor(max_workers=min(5, len(feed_list))) as executor:
            futures = {executor.submit(feed2cubox, cubox_api, url, cubox_tags, cubox_folder, last_time): url 
                      for url in feed_list}
            
            for future in futures:
                feed_url = futures[future]
                try:
                    result = future.result()
                    if result is True:
                        any_success = True
                    elif result is False:
                        logger.warning(f"RSS源处理失败: {feed_url}")
                except Exception as e:
                    all_completed = False
                    logger.error(f"处理RSS源时发生异常: {feed_url} - {e}")
        
        # 根据处理结果更新时间记录
        if all_completed:
            if any_success:
                write_time_log()
                logger.info("所有RSS处理完成，已更新时间记录")
            else:
                logger.info("所有RSS处理完成，但无新内容，时间记录未更新")
        else:
            logger.warning("部分RSS处理异常，时间记录未更新")
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"任务结束，耗时: {duration:.2f}秒")
        logger.info("-" * 50)
        return True
        
    except Exception as e:
        logger.error(f"程序执行过程中发生严重错误: {e}")
        traceback.print_exc()
        logger.info("-" * 50)
        return False


if __name__ == '__main__':
    rss2cubox()
