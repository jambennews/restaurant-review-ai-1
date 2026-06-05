#!/usr/bin/env python3
"""
finance.py - AI团队财务追踪脚本
功能：记录收支、阶梯式再投资分配、月度报表生成、JSON持久化存储
"""

import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum


class InvestmentStage(Enum):
    """投资阶段枚举"""
    SURVIVAL = "生存期"       # 净利润 0-1000
    GROWTH = "增长期"         # 净利润 1000-10000
    # 可扩展更多阶段


@dataclass
class IncomeRecord:
    """收入记录"""
    date: str  # YYYY-MM-DD格式
    client_name: str
    amount: float
    description: str = ""

    def __post_init__(self):
        """验证数据"""
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"日期格式错误: {self.date}，应为YYYY-MM-DD")
        if self.amount <= 0:
            raise ValueError(f"金额必须为正数: {self.amount}")


@dataclass
class ExpenseRecord:
    """支出记录"""
    date: str  # YYYY-MM-DD格式
    expense_type: str
    amount: float
    description: str = ""

    def __post_init__(self):
        """验证数据"""
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"日期格式错误: {self.date}，应为YYYY-MM-DD")
        if self.amount <= 0:
            raise ValueError(f"金额必须为正数: {self.amount}")


@dataclass
class InvestmentAllocation:
    """再投资分配明细"""
    research_development: float = 0.0  # 研发
    reserve: float = 0.0               # 储备
    dividend: float = 0.0              # 分红
    customer_acquisition: float = 0.0  # 获客（仅增长期）

    def total(self) -> float:
        """返回分配总额"""
        return self.research_development + self.reserve + self.dividend + self.customer_acquisition


@dataclass
class MonthlyReport:
    """月度报表"""
    year_month: str  # YYYY-MM格式
    total_income: float = 0.0
    total_expense: float = 0.0
    net_profit: float = 0.0
    cumulative_net_profit: float = 0.0  # 累计净利润（从开始到该月）
    allocation: Optional[InvestmentAllocation] = None


class FinanceTracker:
    """财务追踪器 - 管理AI团队的收支和再投资"""

    # 阶梯式再投资模型配置
    STAGE_CONFIG = {
        InvestmentStage.SURVIVAL: {
            "min": 0,
            "max": 1000,
            "allocation": {
                "research_development": 0.60,
                "reserve": 0.30,
                "dividend": 0.10,
                "customer_acquisition": 0.00,
            }
        },
        InvestmentStage.GROWTH: {
            "min": 1000,
            "max": 10000,
            "allocation": {
                "research_development": 0.30,
                "reserve": 0.20,
                "dividend": 0.10,
                "customer_acquisition": 0.40,
            }
        }
    }

    def __init__(self, data_file: str = "finance_data.json"):
        """
        初始化财务追踪器
        
        Args:
            data_file: JSON数据文件路径
        """
        self.data_file = data_file
        self.incomes: List[IncomeRecord] = []
        self.expenses: List[ExpenseRecord] = []
        self._load_data()

    def _load_data(self) -> None:
        """从JSON文件加载数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.incomes = [IncomeRecord(**item) for item in data.get("incomes", [])]
                    self.expenses = [ExpenseRecord(**item) for item in data.get("expenses", [])]
                print(f"数据已从 {self.data_file} 加载")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"加载数据文件失败: {e}，使用空数据")
                self.incomes = []
                self.expenses = []

    def _save_data(self) -> None:
        """将数据保存到JSON文件"""
        data = {
            "incomes": [asdict(record) for record in self.incomes],
            "expenses": [asdict(record) for record in self.expenses],
            "last_updated": datetime.now().isoformat()
        }
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到 {self.data_file}")
        except IOError as e:
            print(f"保存数据失败: {e}")

    def add_income(self, date_str: str, client_name: str, amount: float, description: str = "") -> IncomeRecord:
        """
        添加收入记录
        
        Args:
            date_str: 日期 (YYYY-MM-DD)
            client_name: 客户名称
            amount: 收入金额
            description: 描述（可选）
            
        Returns:
            创建的IncomeRecord对象
            
        Raises:
            ValueError: 如果参数无效
        """
        record = IncomeRecord(
            date=date_str,
            client_name=client_name,
            amount=amount,
            description=description
        )
        self.incomes.append(record)
        self._save_data()
        print(f"收入记录已添加: {record}")
        return record

    def add_expense(self, date_str: str, expense_type: str, amount: float, description: str = "") -> ExpenseRecord:
        """
        添加支出记录
        
        Args:
            date_str: 日期 (YYYY-MM-DD)
            expense_type: 支出类型（如：研发、市场、运营等）
            amount: 支出金额
            description: 描述（可选）
            
        Returns:
            创建的ExpenseRecord对象
            
        Raises:
            ValueError: 如果参数无效
        """
        record = ExpenseRecord(
            date=date_str,
            expense_type=expense_type,
            amount=amount,
            description=description
        )
        self.expenses.append(record)
        self._save_data()
        print(f"支出记录已添加: {record}")
        return record

    def get_net_profit(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> float:
        """
        计算指定时间范围内的净利润
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)，None表示不限制
            end_date: 结束日期 (YYYY-MM-DD)，None表示不限制
            
        Returns:
            净利润金额
        """
        total_income = sum(
            inc.amount for inc in self.incomes
            if (start_date is None or inc.date >= start_date) and
               (end_date is None or inc.date <= end_date)
        )
        total_expense = sum(
            exp.amount for exp in self.expenses
            if (start_date is None or exp.date >= start_date) and
               (end_date is None or exp.date <= end_date)
        )
        return total_income - total_expense

    def get_cumulative_net_profit(self, up_to_date: Optional[str] = None) -> float:
        """
        计算截至指定日期的累计净利润
        
        Args:
            up_to_date: 截止日期 (YYYY-MM-DD)，None表示所有记录
            
        Returns:
            累计净利润
        """
        return self.get_net_profit(end_date=up_to_date)

    def get_current_stage(self, net_profit: float) -> InvestmentStage:
        """
        根据净利润确定当前投资阶段
        
        Args:
            net_profit: 当前净利润
            
        Returns:
            对应的InvestmentStage枚举值
        """
        for stage, config in self.STAGE_CONFIG.items():
            if config["min"] <= net_profit < config["max"]:
                return stage
        # 如果超过最大范围，返回最后一个阶段
        return InvestmentStage.GROWTH

    def calculate_allocation(self, net_profit: float) -> InvestmentAllocation:
        """
        根据净利润计算再投资分配
        
        Args:
            net_profit: 净利润金额
            
        Returns:
            InvestmentAllocation对象，包含各项分配金额
        """
        if net_profit <= 0:
            return InvestmentAllocation()

        stage = self.get_current_stage(net_profit)
        config = self.STAGE_CONFIG[