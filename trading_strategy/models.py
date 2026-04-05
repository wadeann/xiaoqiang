"""
数据模型模块 - 定义交易中的核心数据结构

包含:
- OHLCVBar: K线数据（开高低收量）
- Trade: 交易记录
- Portfolio: 投资组合状态
- Signal: 交易信号
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalType(Enum):
    """交易信号类型"""
    BUY = "BUY"          # 买入信号
    SELL = "SELL"        # 卖出信号
    HOLD = "HOLD"        # 持有信号


class OrderSide(Enum):
    """订单方向"""
    LONG = "LONG"        # 做多
    SHORT = "SHORT"      # 做空


@dataclass
class OHLCVBar:
    """
    K线数据条
    存储单个时间周期的OHLCV（开高低收量）数据
    """
    timestamp: datetime      # 时间戳
    open: float              # 开盘价
    high: float              # 最高价
    low: float               # 最低价
    close: float             # 收盘价
    volume: float            # 成交量

    @property
    def mid(self) -> float:
        """返回中间价 (最高价+最低价)/2"""
        return (self.high + self.low) / 2

    @property
    def range(self) -> float:
        """返回K线波动范围"""
        return self.high - self.low

    @property
    def body(self) -> float:
        """返回实体大小（收盘价与开盘价之差的绝对值）"""
        return abs(self.close - self.open)


@dataclass
class Signal:
    """
    交易信号
    由策略生成，传递给风控模块审核
    """
    signal_type: SignalType          # 信号类型（买入/卖出/持有）
    timestamp: datetime              # 信号生成时间
    price: float                     # 信号触发价格
    strength: float = 1.0            # 信号强度 (0.0-1.0)
    reason: str = ""                 # 信号生成原因说明

    @property
    def is_actionable(self) -> bool:
        """判断信号是否可执行（非持有信号）"""
        return self.signal_type != SignalType.HOLD


@dataclass
class Trade:
    """
    交易记录
    记录每一笔成交的详细信息
    """
    trade_id: int                    # 交易ID
    side: OrderSide                  # 交易方向
    entry_price: float               # 入场价格
    exit_price: Optional[float] = None  # 出场价格（None表示持仓中）
    quantity: float = 0.0            # 交易数量
    entry_time: Optional[datetime] = None  # 入场时间
    exit_time: Optional[datetime] = None   # 出场时间
    commission: float = 0.0          # 手续费
    slippage: float = 0.0            # 滑点成本
    pnl: float = 0.0                 # 盈亏（已实现）
    pnl_pct: float = 0.0             # 盈亏百分比
    exit_reason: str = ""            # 出场原因

    @property
    def is_open(self) -> bool:
        """判断是否为未平仓交易"""
        return self.exit_price is None

    @property
    def unrealized_pnl(self) -> float:
        """计算未实现盈亏（基于最新价格）"""
        if self.is_open and self.entry_price > 0:
            if self.side == OrderSide.LONG:
                return (self.entry_price - self.entry_price) * self.quantity  # 需要外部传入当前价
            else:
                return (self.entry_price - self.entry_price) * self.quantity
        return 0.0

    @property
    def holding_periods(self) -> Optional[int]:
        """计算持仓周期数（天数）"""
        if self.entry_time and self.exit_time:
            return (self.exit_time - self.entry_time).days
        return None


@dataclass
class Portfolio:
    """
    投资组合状态
    跟踪账户资金、持仓和绩效指标
    """
    initial_capital: float           # 初始资金
    cash: float                      # 当前现金
    position_value: float = 0.0      # 当前持仓市值
    total_value: float = 0.0         # 账户总值
    position_quantity: float = 0.0   # 持仓数量
    position_avg_price: float = 0.0  # 持仓均价
    trades: list = field(default_factory=list)  # 交易记录列表
    equity_curve: list = field(default_factory=list)  # 权益曲线

    def __post_init__(self):
        """初始化后设置总值"""
        self.total_value = self.cash

    @property
    def unrealized_pnl(self) -> float:
        """计算未实现盈亏"""
        if self.position_quantity > 0 and self.position_avg_price > 0:
            return self.position_value - (self.position_avg_price * self.position_quantity)
        return 0.0

    @property
    def total_pnl(self) -> float:
        """计算总盈亏（已实现 + 未实现）"""
        realized = sum(t.pnl for t in self.trades if not t.is_open)
        return realized + self.unrealized_pnl

    @property
    def return_pct(self) -> float:
        """计算总收益率百分比"""
        if self.initial_capital > 0:
            return ((self.total_value - self.initial_capital) / self.initial_capital) * 100
        return 0.0

    @property
    def position_pct(self) -> float:
        """计算持仓占总资产比例"""
        if self.total_value > 0:
            return (self.position_value / self.total_value) * 100
        return 0.0

    def update_equity(self, timestamp: datetime):
        """更新权益曲线记录"""
        self.equity_curve.append({
            "timestamp": timestamp,
            "total_value": self.total_value,
            "cash": self.cash,
            "position_value": self.position_value,
        })

    def summary(self) -> dict:
        """生成投资组合摘要"""
        closed_trades = [t for t in self.trades if not t.is_open]
        wins = [t for t in closed_trades if t.pnl > 0]
        losses = [t for t in closed_trades if t.pnl <= 0]

        return {
            "initial_capital": self.initial_capital,
            "total_value": self.total_value,
            "cash": self.cash,
            "position_value": self.position_value,
            "total_pnl": self.total_pnl,
            "return_pct": round(self.return_pct, 2),
            "position_pct": round(self.position_pct, 2),
            "total_trades": len(self.trades),
            "closed_trades": len(closed_trades),
            "open_trades": len([t for t in self.trades if t.is_open]),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(len(wins) / len(closed_trades) * 100, 2) if closed_trades else 0,
        }
