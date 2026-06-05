#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大众点评/美团差评店铺数据采集爬虫
注意：大众点评有强反爬，可能需手动登录获取cookie
"""

import csv
import random
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

# ==================== 配置区域 ====================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0",
]

# 请求间隔范围（秒）
MIN_DELAY = 2.0
MAX_DELAY = 5.0

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 3.0

# 大众点评搜索URL模板
SEARCH_URL_TEMPLATE = "https://www.dianping.com/search/keyword/{city_id}/{keyword}"

# ==================== 数据结构 ====================
@dataclass
class ShopInfo:
    """店铺信息"""
    name: str = ""               # 店铺名
    category: str = ""           # 类型
    rating: float = 0.0          # 评分
    bad_review_count: int = 0    # 差评数
    total_review_count: int = 0  # 评论数
    address: str = ""            # 地址
    latest_bad_review: str = ""  # 最新差评摘要


# ==================== 工具函数 ====================
def get_random_ua() -> str:
    """随机获取一个User-Agent"""
    return random.choice(USER_AGENTS)


def create_session(cookies: Optional[Dict[str, str]] = None) -> requests.Session:
    """
    创建带随机UA和可选cookie的requests Session
    
    Args:
        cookies: 可选，登录后的cookie字典
        
    Returns:
        配置好的Session对象
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    if cookies:
        session.cookies.update(cookies)
    return session


def safe_request(
    session: requests.Session,
    url: str,
    max_retries: int = MAX_RETRIES,
    delay: float = RETRY_DELAY
) -> Optional[requests.Response]:
    """
    带重试机制的请求函数
    
    Args:
        session: requests Session对象
        url: 请求URL
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        
    Returns:
        成功返回Response，失败返回None
    """
    for attempt in range(max_retries):
        try:
            # 每次重试更换UA
            session.headers.update({"User-Agent": get_random_ua()})
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"[重试 {attempt+1}/{max_retries}] 请求失败: {url}, 错误: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
    return None


def parse_shop_list(html: str) -> List[Dict[str, str]]:
    """
    解析搜索结果页，提取店铺基本信息列表
    
    Args:
        html: 搜索页HTML
        
    Returns:
        店铺基本信息字典列表，每个字典包含 name, url, category
    """
    soup = BeautifulSoup(html, "html.parser")
    shops = []
    
    # 搜索结果店铺列表容器
    shop_items = soup.select("div.shop-list > ul > li")
    if not shop_items:
        # 备用选择器
        shop_items = soup.select("div#shop-all-list > ul > li")
    
    for item in shop_items:
        try:
            # 店铺名和链接
            name_elem = item.select_one("a.shop-name") or item.select_one("h4 a")
            if not name_elem:
                continue
            name = name_elem.get_text(strip=True)
            url = name_elem.get("href", "")
            if url and not url.startswith("http"):
                url = "https://www.dianping.com" + url
            
            # 类型/分类
            cat_elem = item.select_one("span.tag") or item.select_one("span.cate")
            category = cat_elem.get_text(strip=True) if cat_elem else ""
            
            shops.append({
                "name": name,
                "url": url,
                "category": category,
            })
        except Exception as e:
            print(f"解析店铺条目时出错: {e}")
            continue
    
    return shops


def parse_shop_detail(html: str) -> Tuple[float, int, int, str, str]:
    """
    解析店铺详情页，提取评分、评论数、地址、最新差评
    
    Args:
        html: 店铺详情页HTML
        
    Returns:
        (rating, bad_review_count, total_review_count, address, latest_bad_review)
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # 评分
    rating = 0.0
    rating_elem = soup.select_one("span.score") or soup.select_one("span.star-score")
    if rating_elem:
        try:
            rating = float(rating_elem.get_text(strip=True))
        except ValueError:
            pass
    
    # 评论总数
    total_reviews = 0
    review_elem = soup.select_one("span.review-count") or soup.select_one("span.total-review")
    if review_elem:
        try:
            total_reviews = int(review_elem.get_text(strip=True).replace(",", ""))
        except ValueError:
            pass
    
    # 差评数（通常页面不直接显示，需要从评价tab获取）
    # 这里模拟从评价筛选区域提取
    bad_reviews = 0
    bad_elem = soup.select_one("a.bad-review-filter span.num") or \
               soup.select_one("span.bad-count")
    if bad_elem:
        try:
            bad_reviews = int(bad_elem.get_text(strip=True).replace(",", ""))
        except ValueError:
            pass
    
    # 地址
    address = ""
    addr_elem = soup.select_one("span.address") or soup.select_one("div.address span")
    if addr_elem:
        address = addr_elem.get_text(strip=True)
    
    # 最新差评摘要（从评价列表中获取第一条差评）
    latest_bad = ""
    bad_review_items = soup.select("div.review-item.bad") or \
                       soup.select("li.review-item[data-rating='1']") or \
                       soup.select("div.review-list > div.review-item")
    for item in bad_review_items:
        # 尝试获取差评内容
        content_elem = item.select_one("div.review-content") or \
                       item.select_one("p.review-text") or \
                       item.select_one("div.content")
        if content_elem:
            latest_bad = content_elem.get_text(strip=True)[:200]  # 截取前200字
            break
    
    return rating, bad_reviews, total_reviews, address, latest_bad


def get_city_id(city_name: str, session: requests.Session) -> Optional[str]:
    """
    根据城市名获取大众点评城市ID
    
    Args:
        city_name: 城市名（如"北京"）
        session: requests Session
        
    Returns:
        城市ID字符串，失败返回None
    """
    # 城市映射（简化版，实际可能需要动态获取）
    city_map = {
        "北京": "2",
        "上海": "1",
        "广州": "4",
        "深圳": "7",
        "杭州": "3",
        "成都": "8",
        "武汉": "12",
        "南京": "5",
        "重庆": "6",
        "天津": "9",
        "西安": "10",
        "苏州": "11",
    }
    
    if city_name in city_map:
        return city_map[city_name]
    
    # 如果不在映射中，尝试从页面获取
    try:
        url = f"https://www.dianping.com/search/keyword/{city_name}/0"
        resp = safe_request(session, url)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            # 尝试从页面中提取城市ID
            city_elem = soup.select_one("input#cityId") or \
                        soup.select_one("meta[name='cityId']")
            if city_elem:
                return city_elem.get("value") or city_elem.get("content")
    except Exception as e:
        print(f"获取城市ID失败: {e}")
    
    return None


# ==================== 主爬虫函数 ====================
def crawl_bad_review_shops(
    city: str,
    min_reviews: int = 100,
    max_rating: float = 3.5,
    cookies: Optional[Dict[str, str]] = None,
    output_file: str = "bad_review_shops.csv"
) -> List[ShopInfo]:
    """
    采集指定城市的差评店铺数据
    
    Args:
        city: 城市名（如"北京"）
        min_reviews: 最低评论数阈值
        max_rating: 最高评分阈值（低于此评分的店铺视为差评店铺）
        cookies: 可选，登录后的cookie字典
        output_file: 输出CSV文件名
        
    Returns:
        采集到的店铺信息列表
        
    Note:
        大众点评有强反爬，如果遇到验证码或封IP，需要：
        1. 手动登录后获取cookie传入
        2. 使用代理IP
        3. 增加更长的请求间隔
    """
    print(f"开始采集 {city}