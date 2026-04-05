"""
风控管理模块 - 交易风险控制

包含:
- RiskManager: 风控管理器（仓位控制、止损止盈、最大回撤限制）
- PositionSizer: 仓位计算器
"""

from dataclasses import dataclass
from typing import Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import OHLCVBar, OrderSide, Portfolio, Signal, SignalType


@dataclass
class RiskConfig:
    """
    风控配置参数
    
    属性:
        max_position_pct: 单笔最大仓位占比（默认20%）
        stop_loss_pct: 止损百分比（默认5%）
        take_profit_pct: 止盈百分比（默认15%）
        max_drawdown_pct: 最大回撤限制（默认10%）
        max_daily_trades: 每日最大交易次数（默认10次）
        min_signal_strength: 最小信号强度阈值（默认0.3）
        commission_rate: 手续费率（默认0.1%）
        slippage_rate: 滑点率（默认0.05%）
    """
    max_position_pct: float = 0.20        # 单笔最大仓位占比
    stop_loss_pct: float = 0.05           # 止损百分比
    take_profit_pct: float = 0.15         # 止盈百分比
    max_drawdown_pct: float = 0.10        # 最大回撤限制
    max_daily_trades: int = 10            # 每日最大交易次数
    min_signal_strength: float = 0.3      # 最小信号强度
    commission_rate: float = 0.001        # 手续费率
    slippage_rate: float = 0.0005         # 滑点率


class PositionSizer:
    """
    仓位计算器
    
    根据账户资金、风控参数和信号强度计算合适的开仓数量
    支持多种仓位计算模式
    """

    @staticmethod
    def fixed_fraction(
        portfolio: Portfolio,
        price: float,
        risk_pct: float = 0.02,
        stop_loss_pct: float = 0.05,
    ) -> float:
        """
        固定风险比例仓位计算法
        
        公式: 仓位 = (账户总值 × 风险比例) / (价格 × 止损比例)
        确保单笔亏损不超过账户的固定比例
        
        Args:
            portfolio: 投资组合
            price: 当前价格
            risk_pct: 单笔风险比例（默认2%）
            stop_loss_pct: 止损比例（默认5%）
            
        Returns:
            float: 建议开仓数量
        """
        if price <= 0 or stop_loss_pct <= 0:
            return 0.0

        risk_amount = portfolio.total_value * risk_pct
        # 每股风险金额 = 价格 × 止损比例
        risk_per_share = price * stop_loss_pct
        quantity = risk_amount / risk_per_share

        return max(0, quantity)

    @staticmethod
    def percent_of_equity(
        portfolio: Portfolio,
        price: float,
        position_pct: float = 0.20,
    ) -> float:
        """
        固定权益比例仓位计算法
        
        公式: 仓位 = (账户总值 × 仓位比例) / 价格
        
        Args:
            portfolio: 投资组合
            price: 当前价格
            position_pct: 仓位占总权益比例（默认20%）
            
        Returns:
            float: 建议开仓数量
        """
        if price <= 0:
            return 0.0

        position_value = portfolio.total_value * position_pct
        quantity = position_value / price

        return max(0, quantity)


class RiskManager:
    """
    风控管理器
    
    核心功能:
    1. 信号过滤: 过滤强度不足的信号
    2. 仓位控制: 根据风控参数计算开仓数量
    3. 止损止盈: 监控持仓，触发止损止盈
    4. 回撤控制: 监控账户回撤，超限时暂停交易
    5. 交易频率控制: 限制每日交易次数
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self._peak_equity: float = 0.0       # 历史最高权益
        self._daily_trade_count: int = 0     # 当日交易计数
        self._trading_halted: bool = False   # 交易暂停标志
        self.position_sizer = PositionSizer()

    def validate_signal(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        验证信号是否可以通过风控检查
        
        检查项:
        1. 信号强度是否达标
        2. 是否触发最大回撤限制
        3. 是否超过每日交易次数限制
        
        Args:
            signal: 待验证的交易信号
            portfolio: 当前投资组合
            
        Returns:
            bool: 信号是否通过验证
        """
        # 检查交易是否被暂停
        if self._trading_halted:
            return False

        # 检查信号强度
        if signal.strength < self.config.min_signal_strength:
            return False

        # 检查最大回撤
        current_drawdown = self._calc_drawdown(portfolio)
        if current_drawdown > self.config.max_drawdown_pct:
            self._trading_halted = True
            print(f"[风控] 触发最大回撤限制({current_drawdown:.2f}%)，暂停交易")
            return False

        # 检查每日交易次数
        if self._daily_trade_count >= self.config.max_daily_trades:
            return False

        return True

    def calculate_position(
        self,
        signal: Signal,
        portfolio: Portfolio,
    ) -> float:
        """
        计算开仓数量
        
        根据信号强度调整仓位：信号越强，仓位越大（在风控范围内）
        
        Args:
            signal: 交易信号
            portfolio: 当前投资组合
            
        Returns:
            float: 建议开仓数量
        """
        # 根据信号强度动态调整仓位比例
        adjusted_pct = self.config.max_position_pct * signal.strength

        # 使用固定权益比例法计算仓位
        quantity = self.position_sizer.percent_of_equity(
            portfolio=portfolio,
            price=signal.price,
            position_pct=adjusted_pct,
        )

        # 确保不超过可用现金（考虑手续费和滑点）
        cost = quantity * signal.price
        total_cost = cost * (1 + self.config.commission_rate + self.config.slippage_rate)

        if total_cost > portfolio.cash:
            # 现金不足，按最大可买数量计算
            quantity = portfolio.cash / (
                signal.price * (1 + self.config.commission_rate + self.config.slippage_rate)
            )

        return max(0, quantity)

    def check_stop_loss_take_profit(
        self,
        portfolio: Portfolio,
        current_bar: OHLCVBar,
    ) -> Optional[str]:
        """
        检查是否触发止损或止盈
        
        检查逻辑:
        1. 计算当前持仓的盈亏比例
        2. 如果亏损超过止损线 -> 触发止损
        3. 如果盈利超过止盈线 -> 触发止盈
        
        Args:
            portfolio: 当前投资组合
            current_bar: 当前K线数据
            
        Returns:
            str or None: 触发原因（"stop_loss"/"take_profit"），未触发返回None
        """
        if portfolio.position_quantity <= 0 or portfolio.position_avg_price <= 0:
            return None

        # 计算当前盈亏比例
        if portfolio.position_avg_price > 0:
            pnl_pct = (
                (current_bar.close - portfolio.position_avg_price)
                / portfolio.position_avg_price
            )
        else:
            return None

        # 触发止损
        if pnl_pct <= -self.config.stop_loss_pct:
            return "stop_loss"

        # 触发止盈
        if pnl_pct >= self.config.take_profit_pct:
            return "take_profit"

        return None

    def update_peak_equity(self, portfolio: Portfolio):
        """
        更新历史最高权益（用于计算回撤）
        
        Args:
            portfolio: 当前投资组合
        """
        if portfolio.total_value > self._peak_equity:
            self._peak_equity = portfolio.total_value

    def _calc_drawdown(self, portfolio: Portfolio) -> float:
        """
        计算当前回撤比例
        
        回撤 = (最高权益 - 当前权益) / 最高权益
        
        Args:
            portfolio: 当前投资组合
            
        Returns:
            float: 回撤比例（0-1之间）
        """
        if self._peak_equity <= 0:
            return 0.0
        return (self._peak_equity - portfolio.total_value) / self._peak_equity

    def reset_daily_count(self):
        """重置每日交易计数（新交易日开始时调用）"""
        self._daily_trade_count = 0

    def increment_trade_count(self):
        """增加当日交易计数"""
        self._daily_trade_count += 1

    def get_risk_metrics(self, portfolio: Portfolio) -> dict:
        """
        获取当前风控指标
        
        Args:
            portfolio: 当前投资组合
            
        Returns:
            dict: 风控指标字典
        """
        return {
            "peak_equity": self._peak_equity,
            "current_drawdown": round(self._calc_drawdown(portfolio) * 100, 2),
            "max_drawdown_limit": self.config.max_drawdown_pct * 100,
            "daily_trades": self._daily_trade_count,
            "max_daily_trades": self.config.max_daily_trades,
            "trading_halted": self._trading_halted,
            "stop_loss_pct": self.config.stop_loss_pct * 100,
            "take_profit_pct": self.config.take_profit_pct * 100,
        }
