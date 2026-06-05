#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器 - 自动化差评管理流程

功能说明：
    1. 每天定时执行：爬取新线索 → 生成诊断报告 → 推送给商家
    2. 支持配置文件 config.yaml
    3. 任务日志自动归档
    4. 失败重试机制
    5. 完整的函数文档

依赖安装：
    pip install schedule pyyaml requests loguru

使用方法：
    python scheduler.py              # 启动调度器
    python scheduler.py --once       # 立即执行一次完整流程
"""

import os
import sys
import time
import json
import yaml
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum

# 第三方库
try:
    import schedule
    import requests
    from loguru import logger
except ImportError as e:
    print(f"缺少必要依赖: {e}")
    print("请执行: pip install schedule pyyaml requests loguru")
    sys.exit(1)


# ==================== 配置管理 ====================

@dataclass
class Config:
    """配置数据类"""
    api_keys: Dict[str, str] = field(default_factory=dict)
    cities: List[str] = field(default_factory=list)
    push_method: str = "webhook"
    push_url: str = ""
    schedule_time: str = "09:00"
    retry_times: int = 3
    retry_delay: int = 60
    log_dir: str = "logs"
    archive_days: int = 30
    data_dir: str = "data"

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """
        从YAML文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Config实例
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML解析错误
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件 {config_path} 不存在")
        
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
        
        return cls(
            api_keys=raw_config.get("api_keys", {}),
            cities=raw_config.get("cities", []),
            push_method=raw_config.get("push_method", "webhook"),
            push_url=raw_config.get("push_url", ""),
            schedule_time=raw_config.get("schedule_time", "09:00"),
            retry_times=raw_config.get("retry_times", 3),
            retry_delay=raw_config.get("retry_delay", 60),
            log_dir=raw_config.get("log_dir", "logs"),
            archive_days=raw_config.get("archive_days", 30),
            data_dir=raw_config.get("data_dir", "data"),
        )


# ==================== 日志管理 ====================

class LogManager:
    """日志管理器 - 支持自动归档和清理"""
    
    def __init__(self, config: Config):
        """
        初始化日志管理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.log_dir = Path(config.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置loguru
        logger.remove()  # 移除默认handler
        
        # 控制台输出
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True
        )
        
        # 文件输出 - 按天轮转
        logger.add(
            self.log_dir / "scheduler_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="00:00",  # 每天零点轮转
            retention=f"{config.archive_days} days",  # 保留天数
            compression="gz"   # 压缩归档
        )
        
        # 错误日志单独记录
        logger.add(
            self.log_dir / "error_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="ERROR",
            rotation="00:00",
            retention=f"{config.archive_days} days",
            compression="gz"
        )
        
        self._archive_old_logs()
    
    def _archive_old_logs(self):
        """归档旧日志文件"""
        cutoff = datetime.now() - timedelta(days=self.config.archive_days)
        for log_file in self.log_dir.glob("*.log"):
            if log_file.suffix == ".log":
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    # 压缩归档
                    import gzip
                    with open(log_file, "rb") as f_in:
                        with gzip.open(str(log_file) + ".gz", "wb") as f_out:
                            f_out.write(f_in.read())
                    log_file.unlink()
                    logger.info(f"已归档旧日志: {log_file}")


# ==================== 任务状态管理 ====================

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskResult:
    """任务执行结果"""
    task_name: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    data: Any = None


# ==================== 重试机制 ====================

def retry(max_retries: int = 3, delay: int = 60, backoff: float = 2.0):
    """
    重试装饰器 - 支持指数退避
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避因子
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 执行失败 (第{attempt+1}次尝试), "
                            f"{current_delay}秒后重试... 错误: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} 在{max_retries+1}次尝试后仍然失败: {e}"
                        )
                        raise last_exception
            return None
        return wrapper
    return decorator


# ==================== 核心业务模块 ====================

class ReviewCrawler:
    """差评爬取模块"""
    
    def __init__(self, config: Config):
        """
        初始化爬虫
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.data_dir = Path(config.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    @retry(max_retries=3, delay=60)
    def crawl_reviews(self, city: str) -> List[Dict]:
        """
        爬取指定城市的差评数据
        
        Args:
            city: 城市名称
            
        Returns:
            差评数据列表，每个元素为字典格式
            
        Raises:
            requests.RequestException: 网络请求失败
            ValueError: 数据格式异常
        """
        logger.info(f"开始爬取 {city} 的差评数据...")
        
        # 模拟爬取过程 - 实际项目中替换为真实API调用
        mock_data = [
            {
                "id": hashlib.md5(f"{city}_{i}".encode()).hexdigest()[:16],
                "city": city,
                "shop_name": f"店铺_{city}_{i}",
                "rating": 1.0,
                "content": f"这是{city}的第{i}条