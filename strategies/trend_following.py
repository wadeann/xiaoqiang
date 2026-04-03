#!/usr/bin/env python3
"""
小强量化系统 - 趋势跟踪策略
使用移动平均线判断趋势
"""

from typing import List, Dict
from collections import deque


class TrendFollowingStrategy:
    """趋势跟踪策略"""
    
    def __init__(self, ma_short: int = 5, ma_long: int = 20, top_n: int = 3):
        """
        初始化
        
        Args:
            ma_short: 短期均线周期
            ma_long: 长期均线周期
            top_n: 买入前 N 只标的
        """
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.top_n = top_n
        
        # 价格历史缓存
        self.price_history = {}
    
    def update_price(self, symbol: str, price: float):
        """更新价格历史"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.ma_long)
        
        self.price_history[symbol].append(price)
    
    def get_ma(self, symbol: str, period: int) -> float:
        """计算移动平均"""
        if symbol not in self.price_history:
            return None
        
        history = list(self.price_history[symbol])
        if len(history) < period:
            return None
        
        return sum(history[-period:]) / period
    
    def get_trend_signal(self, symbol: str) -> str:
        """
        获取趋势信号
        
        Returns:
            "UP" - 上升趋势
            "DOWN" - 下降趋势
            "NEUTRAL" - 中性
        """
        ma_short = self.get_ma(symbol, self.ma_short)
        ma_long = self.get_ma(symbol, self.ma_long)
        
        if ma_short is None or ma_long is None:
            return "NEUTRAL"
        
        if ma_short > ma_long * 1.02:  # 短期均线高于长期均线 2%
            return "UP"
        elif ma_short < ma_long * 0.98:  # 短期均线低于长期均线 2%
            return "DOWN"
        else:
            return "NEUTRAL"
    
    def generate_signals(self, quotes: List[Dict]) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            quotes: 行情数据列表
        
        Returns:
            交易信号列表
        """
        # 更新价格历史
        for quote in quotes:
            symbol = quote.get("symbol")
            price = quote.get("price")
            if symbol and price:
                self.update_price(symbol, price)
        
        # 分析趋势
        signals = []
        for quote in quotes:
            symbol = quote.get("symbol")
            price = quote.get("price")
            change_pct = quote.get("change_pct", 0)
            
            trend = self.get_trend_signal(symbol)
            ma_short = self.get_ma(symbol, self.ma_short)
            ma_long = self.get_ma(symbol, self.ma_long)
            
            # 上升趋势且当日涨幅 > 3%
            if trend == "UP" and change_pct > 3:
                signals.append({
                    "symbol": symbol,
                    "market": quote.get("market", "US"),
                    "action": "BUY",
                    "change_pct": change_pct,
                    "price": price,
                    "trend": trend,
                    "ma_short": ma_short,
                    "ma_long": ma_long,
                    "reason": f"上升趋势 (MA{self.ma_short}=${ma_short:.2f} > MA{self.ma_long}=${ma_long:.2f})"
                })
        
        # 按涨幅排序
        signals.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
        
        return signals[:self.top_n]
    
    def should_sell(self, position: Dict, current_quote: Dict) -> bool:
        """
        判断是否应该卖出
        
        Args:
            position: 持仓信息
            current_quote: 当前行情
        
        Returns:
            是否卖出
        """
        symbol = position.get("symbol")
        trend = self.get_trend_signal(symbol)
        
        # 下降趋势，卖出
        if trend == "DOWN":
            return True
        
        return False


# 测试代码
if __name__ == "__main__":
    # 模拟行情数据
    test_quotes = [
        {"symbol": "NVDA", "price": 174.0, "change_pct": 5.38, "market": "US"},
        {"symbol": "TSLA", "price": 372.0, "change_pct": 4.82, "market": "US"},
        {"symbol": "ARM", "price": 152.0, "change_pct": 10.5, "market": "US"},
    ]
    
    strategy = TrendFollowingStrategy(ma_short=5, ma_long=20, top_n=3)
    
    # 模拟价格历史
    import random
    for symbol in ["NVDA", "TSLA", "ARM"]:
        base_price = test_quotes[0]["price"] if symbol == "NVDA" else (test_quotes[1]["price"] if symbol == "TSLA" else test_quotes[2]["price"])
        for i in range(25):
            price = base_price * (1 + random.uniform(-0.05, 0.05))
            strategy.update_price(symbol, price)
    
    signals = strategy.generate_signals(test_quotes)
    
    print("趋势跟踪策略信号:")
    for signal in signals:
        print(f"  {signal['action']} {signal['symbol']}: {signal['reason']}")
