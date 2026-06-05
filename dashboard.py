#!/usr/bin/env python3
"""
dashboard.py - 工作目录数据实时统计仪表盘

功能说明：
    读取当前工作目录下的数据文件，在终端输出以下统计信息：
    - 线索数 (Leads)
    - 报告数 (Reports)
    - 推送状态 (Push Status)
    - 本月收支 (Monthly Income/Expense)
    - 净利润 (Net Profit)
    - 再投资分配 (Reinvestment Allocation)

数据来源约定：
    本脚本假设工作目录下存在以下数据文件（格式为CSV或JSON）：
    - leads.csv / leads.json       : 线索数据
    - reports.csv / reports.json   : 报告数据
    - finance.csv / finance.json   : 财务数据（包含收支、推送状态等）
    
    如文件不存在，脚本将尝试从示例数据生成统计信息以便演示。

输出格式：
    纯文本终端输出，无GUI依赖。

依赖：
    Python 3.6+ (标准库，无需额外安装)

作者：AI Assistant
日期：2025-04-10
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple


def read_csv(filepath: str) -> list:
    """
    读取CSV文件并返回字典列表。

    Args:
        filepath: CSV文件路径

    Returns:
        list[dict]: 每行数据作为字典的列表

    Raises:
        FileNotFoundError: 文件不存在时抛出
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def read_json(filepath: str) -> list:
    """
    读取JSON文件并返回数据列表。

    Args:
        filepath: JSON文件路径

    Returns:
        list[dict]: JSON数组内容

    Raises:
        FileNotFoundError: 文件不存在时抛出
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # 如果JSON是字典，尝试提取第一个列表值
            for key, value in data.items():
                if isinstance(value, list):
                    return value
            return [data]
        return []


def load_data(prefix: str) -> list:
    """
    尝试加载指定前缀的CSV或JSON数据文件。

    Args:
        prefix: 文件名前缀 (如 'leads', 'reports', 'finance')

    Returns:
        list[dict]: 加载的数据列表；如果文件都不存在则返回空列表
    """
    # 优先尝试CSV，其次JSON
    for ext in ['.csv', '.json']:
        filepath = os.path.join(os.getcwd(), f"{prefix}{ext}")
        if os.path.exists(filepath):
            try:
                if ext == '.csv':
                    return read_csv(filepath)
                else:
                    return read_json(filepath)
            except Exception as e:
                print(f"警告: 读取 {filepath} 失败: {e}", file=sys.stderr)
                continue
    return []


def calculate_leads(data: list) -> int:
    """
    从线索数据计算线索总数。

    Args:
        data: 线索数据列表

    Returns:
        int: 线索总数
    """
    if not data:
        return 0
    # 尝试多种常见字段名
    for field in ['count', 'leads', 'total', 'value', '数量']:
        if field in data[0]:
            try:
                return sum(int(row.get(field, 0)) for row in data)
            except (ValueError, TypeError):
                continue
    # 默认返回数据行数作为线索数
    return len(data)


def calculate_reports(data: list) -> int:
    """
    从报告数据计算报告总数。

    Args:
        data: 报告数据列表

    Returns:
        int: 报告总数
    """
    if not data:
        return 0
    for field in ['count', 'reports', 'total', '数量']:
        if field in data[0]:
            try:
                return sum(int(row.get(field, 0)) for row in data)
            except (ValueError, TypeError):
                continue
    return len(data)


def calculate_finance(data: list) -> Tuple[float, float, float, str]:
    """
    从财务数据计算收支、净利润和推送状态。

    Args:
        data: 财务数据列表

    Returns:
        Tuple[float, float, float, str]: (收入, 支出, 净利润, 推送状态文本)
    """
    income = 0.0
    expense = 0.0
    push_status = "未知"

    if not data:
        return income, expense, 0.0, push_status

    # 尝试从字段中提取收入/支出
    for row in data:
        # 收入字段
        for inc_field in ['income', 'revenue', '收入', 'in']:
            if inc_field in row:
                try:
                    income += float(row[inc_field])
                except (ValueError, TypeError):
                    pass
                break

        # 支出字段
        for exp_field in ['expense', 'cost', '支出', 'out']:
            if exp_field in row:
                try:
                    expense += float(row[exp_field])
                except (ValueError, TypeError):
                    pass
                break

        # 推送状态字段
        for status_field in ['status', 'push_status', '推送状态', 'state']:
            if status_field in row:
                push_status = str(row[status_field])
                break

    net_profit = income - expense
    return income, expense, net_profit, push_status


def calculate_reinvestment(net_profit: float) -> float:
    """
    根据净利润计算再投资分配（默认分配30%）。

    Args:
        net_profit: 净利润

    Returns:
        float: 再投资金额
    """
    # 可配置的再投资比例
    reinvestment_ratio = 0.30
    reinvestment = net_profit * reinvestment_ratio
    return max(0.0, reinvestment)  # 净利润为负时不分配


def generate_sample_data() -> Dict:
    """
    生成示例统计数据（当没有数据文件时使用）。

    Returns:
        dict: 包含所有统计字段的字典
    """
    return {
        'leads': 128,
        'reports': 47,
        'income': 85000.00,
        'expense':