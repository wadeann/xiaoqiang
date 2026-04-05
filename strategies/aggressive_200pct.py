"""
200%年收益激进策略 - 三套方案对比验证

目标：年化收益率 200% (月均 16.7%)

核心思路：
1. 放大仓位 (单笔 30-40% vs 原来 15%)
2. 延长止盈 (+60% vs 原来 +12%)
3. 抓龙头股 (涨幅 >20% 强势股)
4. 快速轮动 (持仓周期 5-15天)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from models import OHLCVBar, Signal, SignalType, Portfolio, Trade
from strategies.momentum import BaseStrategy


@dataclass
class Aggressive200Config:
    """
    200%年收益策略配置
    
    关键参数：
    - position_size: 0.35 (单笔仓位35%，原来15%)
    - stop_loss: -0.10 (止损-10%)
    - take_profit_1: 0.30 (第一止盈点30%)
    - take_profit_2: 0.60 (第二止盈点60%)
    - trailing_stop: 0.15 (移动止损15%，从最高点)
    - max_hold_days: 15 (最长持仓15天)
    """
    position_size: float = 0.35      # 单笔仓位
    stop_loss: float = -0.10         # 止损线
    take_profit_1: float = 0.30      # 第一止盈(卖出50%)
    take_profit_2: float = 0.60      # 第二止盈(清仓)
    trailing_stop: float = 0.15      # 移动止损
    max_hold_days: int = 15          # 最长持仓天数
    min_strength: float = 0.6        # 最小信号强度
    max_positions: int = 3           # 最大持仓数(集中火力)


class DragonCatcher(BaseStrategy):
    """
    龙头捕获策略 - 专抓强势股
    
    选股条件：
    1. 5日涨幅 > 15%
    2. RSI 在 50-70 区间
    3. 成交量放大 > 2x
    4. 刚突破 MA5
    5. 属于热门板块
    """
    
    def __init__(self, config: Aggressive200Config = None):
        super().__init__("DragonCatcher")
        self.config = config or Aggressive200Config()
        self._highest_prices = {}  # 记录最高价
        
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """生成激进买入信号"""
        
        # 数据不足，返回HOLD
        if len(self._bars) < 5:
            return Signal(
                signal_type=SignalType.HOLD,
                timestamp=bar.timestamp,
                price=bar.close,
                reason="数据不足"
            )
        
        # 计算5日涨幅
        if len(self._bars) >= 5:
            start_price = self._bars[-5].close
            pct_change = (bar.close - start_price) / start_price
            
            # 计算RSI (简化版)
            gains = []
            losses = []
            for i in range(1, min(15, len(self._bars))):
                change = self._bars[-i].close - self._bars[-i-1].close
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            # 计算成交量比率
            avg_volume = sum([b.volume for b in self._bars[-5:]]) / 5
            volume_ratio = bar.volume / avg_volume if avg_volume > 0 else 1
            
            # 计算MA5
            ma5 = sum([b.close for b in self._bars[-5:]]) / 5
            
            # 龙头捕获条件 (非常激进)
            if pct_change > 0.15 and \
               50 <= rsi <= 70 and \
               volume_ratio > 2.0 and \
               bar.close > ma5:
                
                strength = min(1.0, pct_change * 3 + (volume_ratio - 1) * 0.3)
                
                return Signal(
                    signal_type=SignalType.BUY,
                    timestamp=bar.timestamp,
                    price=bar.close,
                    strength=strength,
                    reason=f"龙头信号: 5日涨幅{pct_change*100:.1f}%, RSI{rsi:.1f}, 成交量{volume_ratio:.1f}x"
                )
        
        return Signal(
            signal_type=SignalType.HOLD,
            timestamp=bar.timestamp,
            price=bar.close,
            reason="未达到龙头条件"
        )


class MomentumRocket(BaseStrategy):
    """
    动量火箭策略 - 快速爆发
    
    选股条件：
    1. 3日涨幅 > 8%
    2. 连续3天上涨
    3. 成交量逐日放大
    4. MACD金叉
    """
    
    def __init__(self, config: Aggressive200Config = None):
        super().__init__("MomentumRocket")
        self.config = config or Aggressive200Config()
        
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """生成快速动量信号"""
        
        if len(self._bars) < 10:
            return Signal(
                signal_type=SignalType.HOLD,
                timestamp=bar.timestamp,
                price=bar.close,
                reason="数据不足"
            )
        
        # 3日涨幅
        if len(self._bars) >= 3:
            start_price = self._bars[-3].close
            pct_change = (bar.close - start_price) / start_price
            
            # 连续上涨检查
            consecutive_up = all([
                self._bars[-i].close > self._bars[-i-1].close 
                for i in range(1, 3)
            ])
            
            # 成交量放大检查
            volume_expanding = all([
                self._bars[-i].volume > self._bars[-i-1].volume 
                for i in range(1, 3)
            ])
            
            # MACD金叉 (简化)
            ema12 = sum([b.close for b in self._bars[-12:]]) / 12
            ema26 = sum([b.close for b in self._bars[-26:]]) / 26 if len(self._bars) >= 26 else ema12
            macd = ema12 - ema26
            
            prev_ema12 = sum([b.close for b in self._bars[-13:-1]]) / 12
            prev_ema26 = sum([b.close for b in self._bars[-27:-1]]) / 26 if len(self._bars) >= 27 else prev_ema12
            prev_macd = prev_ema12 - prev_ema26
            
            macd_cross = macd > prev_macd and prev_macd < 0
            
            # 火箭条件
            if pct_change > 0.08 and \
               consecutive_up and \
               volume_expanding and \
               macd_cross:
                
                strength = pct_change * 4 + 0.2
                
                return Signal(
                    signal_type=SignalType.BUY,
                    timestamp=bar.timestamp,
                    price=bar.close,
                    strength=min(1.0, strength),
                    reason=f"火箭信号: 3日涨幅{pct_change*100:.1f}%, 连续上涨, 成交量放大"
                )
        
        return Signal(
            signal_type=SignalType.HOLD,
            timestamp=bar.timestamp,
            price=bar.close,
            reason="未达到火箭条件"
        )


class SectorRotation(BaseStrategy):
    """
    板块轮动策略 - 抓板块切换
    
    选股条件：
    1. 板块热度排名第一
    2. 个股涨幅在板块内前3
    3. 板块成交量暴增
    4. 资金流入明显
    """
    
    def __init__(self, config: Aggressive200Config = None):
        super().__init__("SectorRotation")
        self.config = config or Aggressive200Config()
        
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """生成板块轮动信号"""
        
        # 这里简化处理，实际需要板块数据
        if len(self._bars) < 20:
            return Signal(
                signal_type=SignalType.HOLD,
                timestamp=bar.timestamp,
                price=bar.close,
                reason="数据不足"
            )
        
        # 20日涨幅排名模拟
        if len(self._bars) >= 20:
            start_price = self._bars[-20].close
            pct_change = (bar.close - start_price) / start_price
            
            # 成交量激增
            avg_volume_20 = sum([b.volume for b in self._bars[-20:]) / 20
            avg_volume_5 = sum([b.volume for b in self._bars[-5:]) / 5
            volume_surge = avg_volume_5 / avg_volume_20 if avg_volume_20 > 0 else 1
            
            # 板块轮动条件 (假设涨幅>30%代表热门板块)
            if pct_change > 0.30 and volume_surge > 1.5:
                
                return Signal(
                    signal_type=SignalType.BUY,
                    timestamp=bar.timestamp,
                    price=bar.close,
                    strength=0.8,
                    reason=f"板块轮动: 20日涨幅{pct_change*100:.1f}%, 成交量激增{volume_surge:.1f}x"
                )
        
        return Signal(
            signal_type=SignalType.HOLD,
            timestamp=bar.timestamp,
            price=bar.close,
            reason="未达到板块轮动条件"
        )


# 策略组合
STRATEGY_SETS = {
    "aggressive_200": {
        "name": "200%激进组合",
        "strategies": [DragonCatcher, MomentumRocket, SectorRotation],
        "weights": [0.4, 0.35, 0.25],  # 策略权重
        "config": Aggressive200Config(),
        "target_return": 2.0  # 200%
    },
    "dragon_only": {
        "name": "龙头单一策略",
        "strategies": [DragonCatcher],
        "weights": [1.0],
        "config": Aggressive200Config(),
        "target_return": 2.5  # 250%
    },
    "rocket_combo": {
        "name": "火箭动量组合",
        "strategies": [MomentumRocket, DragonCatcher],
        "weights": [0.6, 0.4],
        "config": Aggressive200Config(),
        "target_return": 2.0
    }
}