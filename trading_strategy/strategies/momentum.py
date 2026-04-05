"""
动量策略模块 - 基于价格和成交量动量的交易策略

包含:
- BaseStrategy: 策略基类
- MomentumStrategy: 双均线动量策略
- RSIMomentumStrategy: RSI动量策略
"""

from abc import ABC, abstractmethod
from typing import List, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import OHLCVBar, Signal, SignalType


class BaseStrategy(ABC):
    """
    策略基类
    所有交易策略都应继承此类并实现 generate_signal 方法
    """

    def __init__(self, name: str):
        self.name = name
        self._bars: List[OHLCVBar] = []  # 存储历史K线数据

    @abstractmethod
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """
        生成交易信号（子类必须实现）
        
        Args:
            bar: 当前K线数据
            
        Returns:
            Signal: 交易信号
        """
        pass

    def update(self, bar: OHLCVBar):
        """
        更新策略数据（每根新K线调用）
        
        Args:
            bar: 新的K线数据
        """
        self._bars.append(bar)

    @property
    def bars(self) -> List[OHLCVBar]:
        """返回历史K线数据"""
        return self._bars

    @property
    def lookback(self) -> int:
        """返回已有数据长度"""
        return len(self._bars)


class MomentumStrategy(BaseStrategy):
    """
    双均线动量策略
    
    策略逻辑:
    - 短期均线上穿长期均线 -> 买入信号（金叉）
    - 短期均线下穿长期均线 -> 卖出信号（死叉）
    - 结合成交量确认信号强度
    
    参数:
        fast_period: 短期均线周期（默认5）
        slow_period: 长期均线周期（默认20）
        volume_threshold: 成交量确认阈值（默认1.0，表示不低于平均成交量）
    """

    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 20,
        volume_threshold: float = 1.0,
    ):
        super().__init__(name="Dual_MA_Momentum")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.volume_threshold = volume_threshold
        self._prev_fast_ma: Optional[float] = None  # 上一期短期均线值
        self._prev_slow_ma: Optional[float] = None  # 上一期长期均线值

    def _calc_sma(self, period: int) -> Optional[float]:
        """
        计算简单移动平均线 (SMA)
        
        Args:
            period: 计算周期
            
        Returns:
            float or None: SMA值，数据不足时返回None
        """
        if self.lookback < period:
            return None
        # 取最近period根K线的收盘价计算均值
        closes = [bar.close for bar in self._bars[-period:]]
        return sum(closes) / period

    def _calc_volume_ratio(self) -> float:
        """
        计算成交量相对比率（当前成交量 / 平均成交量）
        
        Returns:
            float: 成交量比率，数据不足时返回1.0
        """
        if self.lookback < 20:
            return 1.0
        avg_volume = sum(bar.volume for bar in self._bars[-20:-1]) / 19
        if avg_volume == 0:
            return 1.0
        return self._bars[-1].volume / avg_volume

    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """
        生成动量交易信号
        
        信号规则:
        1. 金叉 + 放量 -> 强买入信号
        2. 金叉 + 缩量 -> 弱买入信号
        3. 死叉 -> 卖出信号
        4. 无交叉 -> 持有信号
        
        Args:
            bar: 当前K线数据
            
        Returns:
            Signal: 交易信号
        """
        # 计算当前均线
        fast_ma = self._calc_sma(self.fast_period)
        slow_ma = self._calc_sma(self.slow_period)

        # 数据不足时返回持有信号
        if fast_ma is None or slow_ma is None:
            return Signal(
                signal_type=SignalType.HOLD,
                timestamp=bar.timestamp,
                price=bar.close,
                reason="数据不足，等待更多K线",
            )

        signal_type = SignalType.HOLD
        strength = 0.5
        reason = ""

        # 检测金叉/死叉
        if self._prev_fast_ma is not None and self._prev_slow_ma is not None:
            # 金叉: 短期均线从下方穿越长期均线
            if self._prev_fast_ma <= self._prev_slow_ma and fast_ma > slow_ma:
                signal_type = SignalType.BUY
                volume_ratio = self._calc_volume_ratio()
                # 根据成交量调整信号强度
                if volume_ratio >= self.volume_threshold:
                    strength = min(1.0, volume_ratio / 2.0)
                    reason = f"金叉确认，放量{volume_ratio:.2f}倍"
                else:
                    strength = 0.5
                    reason = f"金叉但缩量，成交量比率{volume_ratio:.2f}"

            # 死叉: 短期均线从上方穿越长期均线
            elif self._prev_fast_ma >= self._prev_slow_ma and fast_ma < slow_ma:
                signal_type = SignalType.SELL
                strength = 0.8
                reason = "死叉确认，趋势转弱"

        # 更新上一期均线值
        self._prev_fast_ma = fast_ma
        self._prev_slow_ma = slow_ma

        return Signal(
            signal_type=signal_type,
            timestamp=bar.timestamp,
            price=bar.close,
            strength=strength,
            reason=reason,
        )


class RSIMomentumStrategy(BaseStrategy):
    """
    RSI动量策略
    
    策略逻辑:
    - RSI < 超卖线(30) -> 买入信号（超卖反弹）
    - RSI > 超买线(70) -> 卖出信号（超买回落）
    - RSI在中间区域 -> 持有信号
    
    参数:
        rsi_period: RSI计算周期（默认14）
        overbought: 超买阈值（默认70）
        oversold: 超卖阈值（默认30）
    """

    def __init__(
        self,
        rsi_period: int = 14,
        overbought: float = 70,
        oversold: float = 30,
    ):
        super().__init__(name="RSI_Momentum")
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.oversold = oversold
        self._gains: List[float] = []  # 上涨幅度记录
        self._losses: List[float] = []  # 下跌幅度记录

    def _calc_rsi(self) -> Optional[float]:
        """
        计算RSI指标 (Relative Strength Index)
        
        RSI = 100 - (100 / (1 + RS))
        RS = 平均涨幅 / 平均跌幅
        
        Returns:
            float or None: RSI值，数据不足时返回None
        """
        if self.lookback < self.rsi_period + 1:
            return None

        # 计算最近N期的涨跌幅
        gains = []
        losses = []
        for i in range(-self.rsi_period, 0):
            change = self._bars[i].close - self._bars[i - 1].close
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains) / self.rsi_period
        avg_loss = sum(losses) / self.rsi_period

        # 防止除以0
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """
        生成RSI交易信号
        
        Args:
            bar: 当前K线数据
            
        Returns:
            Signal: 交易信号
        """
        rsi = self._calc_rsi()

        if rsi is None:
            return Signal(
                signal_type=SignalType.HOLD,
                timestamp=bar.timestamp,
                price=bar.close,
                reason="数据不足，无法计算RSI",
            )

        signal_type = SignalType.HOLD
        strength = 0.5
        reason = f"RSI={rsi:.2f}"

        # 超卖区域 -> 买入信号
        if rsi < self.oversold:
            signal_type = SignalType.BUY
            # 越接近0信号越强
            strength = min(1.0, (self.oversold - rsi) / self.oversold)
            reason = f"RSI超卖({rsi:.2f}<{self.oversold})，可能反弹"

        # 超买区域 -> 卖出信号
        elif rsi > self.overbought:
            signal_type = SignalType.SELL
            # 越接近100信号越强
            strength = min(1.0, (rsi - self.overbought) / (100 - self.overbought))
            reason = f"RSI超买({rsi:.2f}>{self.overbought})，可能回落"

        return Signal(
            signal_type=signal_type,
            timestamp=bar.timestamp,
            price=bar.close,
            strength=strength,
            reason=reason,
        )
