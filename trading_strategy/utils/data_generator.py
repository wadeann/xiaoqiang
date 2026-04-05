"""
数据生成工具 - 生成模拟K线数据用于回测测试
"""

import math
import random
from datetime import datetime, timedelta
from typing import List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import OHLCVBar


def generate_sample_bars(
    start_date: datetime = None,
    num_bars: int = 200,
    initial_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.0005,
    seed: int = None,
) -> List[OHLCVBar]:
    """
    生成模拟K线数据
    
    使用几何布朗运动模拟价格走势，包含趋势和波动
    
    Args:
        start_date: 起始日期（默认2024-01-01）
        num_bars: K线数量（默认200）
        initial_price: 初始价格（默认100）
        volatility: 日波动率（默认2%）
        trend: 日趋势（默认0.05%）
        seed: 随机种子（用于复现结果）
        
    Returns:
        List[OHLCVBar]: 模拟K线数据列表
    """
    if seed is not None:
        random.seed(seed)

    if start_date is None:
        start_date = datetime(2024, 1, 1)

    bars = []
    price = initial_price

    for i in range(num_bars):
        # 几何布朗运动生成价格变化
        drift = trend
        shock = volatility * random.gauss(0, 1)
        price *= math.exp(drift + shock)

        # 生成OHLCV
        daily_range = price * volatility * random.uniform(0.5, 2.0)
        open_price = price * (1 + random.uniform(-0.005, 0.005))
        high_price = max(open_price, price) + daily_range * random.uniform(0, 0.5)
        low_price = min(open_price, price) - daily_range * random.uniform(0, 0.5)
        volume = random.uniform(1000000, 5000000) * (1 + abs(shock) * 5)  # 波动大时放量

        bar = OHLCVBar(
            timestamp=start_date + timedelta(days=i),
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(price, 2),
            volume=round(volume, 0),
        )
        bars.append(bar)

    return bars
