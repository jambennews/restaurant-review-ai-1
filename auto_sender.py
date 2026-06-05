#!/usr/bin/env python3
"""
auto_sender.py - 诊断报告自动推送脚本
支持邮件(SMTP)、企业微信机器人Webhook、飞书机器人三种推送方式
"""

import csv
import json
import logging
import os
import smtplib
import time
from dataclasses import dataclass, field
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ==================== 配置区域 ====================

# 日志配置
LOG_FILE = "push_log.txt"
LOG_LEVEL = logging.INFO

# 速率控制：每分钟最多推送数量
RATE_LIMIT_PER_MINUTE = 5

# 邮件SMTP配置（示例，请根据实际情况修改）
SMTP_CONFIG = {
    "host": "smtp.example.com",
    "port": 465,
    "use_ssl": True,
    "username": "your_email@example.com",
    "password": "your_password",
}

# 默认发件人名称和地址
DEFAULT_SENDER_NAME = "诊断报告系统"
DEFAULT_SENDER_EMAIL = "noreply@example.com"

# ==================== 数据结构 ====================


@dataclass
class MerchantInfo:
    """商家信息数据类"""

    name: str  # 商家名称
    email: Optional[str] = None  # 邮箱地址（邮件推送时使用）
    wecom_webhook: Optional[str] = None  # 企业微信机器人Webhook地址
    feishu_webhook: Optional[str] = None  # 飞书机器人Webhook地址
    extra: Dict[str, str] = field(default_factory=dict)  # 额外字段，用于模板变量

    def __post_init__(self) -> None:
        """初始化后校验至少有一种推送方式"""
        if not any([self.email, self.wecom_webhook, self.feishu_webhook]):
            raise ValueError(f"商家 '{self.name}' 未配置任何推送方式")


@dataclass
class PushResult:
    """推送结果数据类"""

    merchant_name: str
    push_type: str  # email / wecom / feishu
    success: bool
    timestamp: float
    error_message: Optional[str] = None


# ==================== 日志配置 ====================


def setup_logger(log_file: str = LOG_FILE, level: int = LOG_LEVEL) -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        log_file: 日志文件路径
        level: 日志级别

    Returns:
        配置好的Logger对象
    """
    logger = logging.getLogger("AutoSender")
    logger.setLevel(level)

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # 避免重复添加处理器
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()


# ==================== 模板引擎 ====================


def render_template(template: str, variables: Dict[str, str]) -> str:
    """
    渲染模板字符串，替换变量占位符

    支持的变量格式: {变量名}
    预定义变量: {商家名}, {报告路径}, {报告文件名}

    Args:
        template: 模板字符串
        variables: 变量字典

    Returns:
        渲染后的字符串
    """
    # 确保预定义变量存在
    default_vars = {
        "商家名": variables.get("name", ""),
        "报告路径": variables.get("report_path", ""),
        "报告文件名": os.path.basename(variables.get("report_path", "")),
    }
    all_vars = {**default_vars, **variables}

    result = template
    for key, value in all_vars.items():
        placeholder = "{" + key + "}"
        result = result.replace(placeholder, str(value))

    return result


# ==================== 推送器基类 ====================


class BasePusher:
    """推送器基类"""

    def push(
        self, merchant: MerchantInfo, report_path: str, template_vars: Dict[str, str]
    ) -> PushResult:
        """
        执行推送操作（子类需实现）

        Args:
            merchant: 商家信息
            report_path: 报告文件路径
            template_vars: 模板变量

        Returns:
            推送结果
        """
        raise NotImplementedError


# ==================== 邮件推送 ====================


class EmailPusher(BasePusher):
    """邮件推送器"""

    def __init__(
        self,
        smtp_config: Dict[str, Any],
        sender_name: str = DEFAULT_SENDER_NAME,
        sender_email: str = DEFAULT_SENDER_EMAIL,
    ) -> None:
        """
        初始化邮件推送器

        Args:
            smtp_config: SMTP配置字典，包含host, port, use_ssl, username, password
            sender_name: 发件人名称
            sender_email: 发件人邮箱
        """
        self.smtp_config = smtp_config
        self.sender_name = sender_name
        self.sender_email = sender_email

    def push(
        self, merchant: MerchantInfo, report_path: str, template_vars: Dict[str, str]
    ) -> PushResult:
        """
        发送邮件推送

        Args:
            merchant: 商家信息（需包含email字段）
            report_path: 报告文件路径
            template_vars: 模板变量

        Returns:
            推送结果
        """
        start_time = time.time()

        if not merchant.email:
            return PushResult(
                merchant_name=merchant.name,
                push_type="email",
                success=False,
                timestamp=start_time,
                error_message="商家未配置邮箱地址",
            )

        try:
            # 构建邮件
            msg = MIMEMultipart()
            msg["From"] = formataddr((self.sender_name, self.sender_email))
            msg["To"] = merchant.email

            # 邮件主题和正文（支持模板）
            subject_template = "诊断报告 - {商家名}"
            body_template = (
                "尊敬的{商家名}，\n\n"
                "您好！请查收您的诊断报告。\n"
                "报告文件：{报告文件名}\n"
                "报告路径：{报告路径}\n\n"
                "此邮件由系统自动发送，请勿回复。"
            )

            msg["Subject"] = render_template(subject_template, template_vars)
            msg.attach(MIMEText(render_template(body_template, template_vars), "plain", "utf-8"))

            # 添加附件
            report_path_obj = Path(report_path)
            if report_path_obj.exists():
                with open(report_path_obj, "rb") as f:
                    attachment = MIMEApplication(f.read(), _subtype="octet-stream")
                    attachment.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=report_path_obj.name,
                    )
                    msg.attach(attachment)
            else:
                logger.warning(f"报告文件不存在: {report_path}")

            # 发送邮件
            if self.smtp_config.get("use_ssl", True):
                with smtplib.SMTP_SSL(
                    self.smtp_config["host"], self.smtp_config.get("port", 465)
                ) as server:
                    server.login(
                        self.smtp_config["username"], self.smtp_config["password"]
                    )
                    server.sendmail(self.sender_email, [merchant.email], msg.as_string())
            else:
                with smtplib.SMTP(
                    self.smtp_config["host"], self.smtp_config.get("port", 587)
                ) as server:
                    server.starttls()
                    server.login(
                        self.smtp_config["username"], self.smtp_config["password"]
                    )
                    server.sendmail(self.sender_email, [merchant.email], msg.as_string())

            return PushResult(
                merchant_name=merchant.name,
                push_type="email",
                success=True,
                timestamp=time.time(),
            )

        except Exception as e:
            error_msg = f"邮件推送失败: {str(e)}"
            logger.error(error_msg)
            return PushResult(
                merchant_name=merchant.name,
                push_type="email",
                success=False,
                timestamp=time.time(),
                error_message=error_msg,
            )


# ==================== 企业微信机器人推送