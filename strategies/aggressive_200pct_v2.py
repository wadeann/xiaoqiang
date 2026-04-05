"""
200%年收益激进策略 v2 - 简化版

目标：年化收益率 200%
核心：高仓位 + 龙头股 + 快速轮动
"""

import sys
import os
sys.path.append('/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang')

from dataclasses import dataclass
from typing import List
from datetime import datetime

from trading_strategy.models import OHLCVBar, Signal, SignalType
from trading_strategy.strategies.momentum import BaseStrategy


@dataclass
class AggressiveConfig:
    """200%年收益策略配置"""
    position_size: float = 0.35      # 单笔仓位35%
    stop_loss: float = -0.10         # 止损-10%
    take_profit_1: float = 0.30      # 第一止盈30%
    take_profit_2: float = 0.60      # 第二止盈60%
    trailing_stop: float = 0.15      # 移动止损15%
    max_hold_days: int = 15          # 最长持仓15天
    min_strength: float = 0.6        # 最小信号强度
    max_positions: int = 3           # 最大持仓3只


class DragonStrategy(BaseStrategy):
    """龙头捕获策略 - 抓强势股"""
    
    def __init__(self, config: AggressiveConfig = None):
        super().__init__("DragonStrategy")
        self.config = config or AggressiveConfig()
        
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """生成买入信号"""
        
        if len(self._bars) < 5:
            return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="数据不足")
        
        # 计算5日涨幅
        start_price = self._bars[-5].close
        pct_change = (bar.close - start_price) / start_price
        
        # 计算RSI
        gains = []
        losses = []
        for i in range(1, min(15, len(self._bars))):
            change = self._bars[-i].close - self._bars[-i-1].close
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0.001
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # 计算成交量比率
        volumes = [b.volume for b in self._bars[-5:]]
        avg_volume = sum(volumes) / len(volumes)
        volume_ratio = bar.volume / avg_volume if avg_volume > 0 else 1
        
        # 计算MA5
        closes = [b.close for b in self._bars[-5:]]
        ma5 = sum(closes) / len(closes)
        
        # 龙头条件
        if pct_change > 0.15 and 50 <= rsi <= 70 and volume_ratio > 2.0 and bar.close > ma5:
            strength = min(1.0, pct_change * 3 + (volume_ratio - 1) * 0.3)
            return Signal(
                SignalType.BUY, bar.timestamp, bar.close, strength,
                f"龙头: 涨幅{pct_change*100:.1f}%, RSI{rsi:.0f}, 量比{volume_ratio:.1f}x"
            )
        
        return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="未达龙头条件")


class RocketStrategy(BaseStrategy):
    """动量火箭策略 - 快速爆发"""
    
    def __init__(self, config: AggressiveConfig = None):
        super().__init__("RocketStrategy")
        self.config = config or AggressiveConfig()
        
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """生成快速动量信号"""
        
        if len(self._bars) < 10:
            return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="数据不足")
        
        # 3日涨幅
        start_price = self._bars[-3].close
        pct_change = (bar.close - start_price) / start_price
        
        # 连续上涨
        consecutive_up = (
            self._bars[-1].close > self._bars[-2].close and
            self._bars[-2].close > self._bars[-3].close
        )
        
        # 成交量放大
        volume_expanding = (
            self._bars[-1].volume > self._bars[-2].volume and
            self._bars[-2].volume > self._bars[-3].volume
        )
        
        # 火箭条件
        if pct_change > 0.08 and consecutive_up and volume_expanding:
            strength = min(1.0, pct_change * 4 + 0.2)
            return Signal(
                SignalType.BUY, bar.timestamp, bar.close, strength,
                f"火箭: 3日涨幅{pct_change*100:.1f}%, 连涨, 量增"
            )
        
        return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="未达火箭条件")


class SectorRotationStrategy(BaseStrategy):
    """板块轮动策略 - 抓板块切换"""
    
    def __init__(self, config: AggressiveConfig = None):
        super().__init__("SectorRotationStrategy")
        self.config = config or AggressiveConfig()
        
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """生成板块轮动信号"""
        
        if len(self._bars) < 20:
            return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="数据不足")
        
        # 20日涨幅
        start_price = self._bars[-20].close
        pct_change = (bar.close - start_price) / start_price
        
        # 成交量激增
        volumes_20 = [b.volume for b in self._bars[-20:]]
        volumes_5 = [b.volume for b in self._bars[-5:]]
        avg_volume_20 = sum(volumes_20) / len(volumes_20)
        avg_volume_5 = sum(volumes_5) / len(volumes_5)
        volume_surge = avg_volume_5 / avg_volume_20 if avg_volume_20 > 0 else 1
        
        # 板块轮动条件
        if pct_change > 0.30 and volume_surge > 1.5:
            return Signal(
                SignalType.BUY, bar.timestamp, bar.close, 0.8,
                f"板块轮动: 20日涨幅{pct_change*100:.1f}%, 量激增{volume_surge:.1f}x"
            )
        
        return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="未达板块轮动条件")


# 策略配置
STRATEGY_CONFIGS = {
    "dragon": {
        "name": "龙头捕获",
        "strategy": DragonStrategy,
        "target": 2.5  # 250%年化
    },
    "rocket": {
        "name": "动量火箭",
        "strategy": RocketStrategy,
        "target": 2.0  # 200%年化
    },
    "rotation": {
        "name": "板块轮动",
        "strategy": SectorRotationStrategy,
        "target": 1.8  # 180%年化
    }
}