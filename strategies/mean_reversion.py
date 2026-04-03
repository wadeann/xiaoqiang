#!/usr/bin/env python3
"""
小强量化系统 - 均值回归策略
买入跌幅最大的标的，期待反弹
"""

from typing import List, Dict


class MeanReversionStrategy:
    """均值回归策略"""
    
    def __init__(self, top_n: int = 3, max_drop_pct: float = -3.0):
        """
        初始化
        
        Args:
            top_n: 买入前 N 只标的
            max_drop_pct: 最大跌幅阈值 (%)，低于此值才买入
        """
        self.top_n = top_n
        self.max_drop_pct = max_drop_pct
    
    def generate_signals(self, quotes: List[Dict]) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            quotes: 行情数据列表
        
        Returns:
            交易信号列表
        """
        # 过滤跌幅大于阈值的标的
        dropped_stocks = [q for q in quotes if q.get("change_pct", 0) <= self.max_drop_pct]
        
        # 按跌幅排序 (跌幅最大的在前)
        dropped_stocks.sort(key=lambda x: x.get("change_pct", 0))
        
        # 取前 N 只
        top_dropped = dropped_stocks[:self.top_n]
        
        # 生成买入信号
        signals = []
        for stock in top_dropped:
            signals.append({
                "symbol": stock.get("symbol"),
                "market": stock.get("market", "US"),
                "action": "BUY",
                "change_pct": stock.get("change_pct", 0),
                "price": stock.get("price"),
                "reason": f"跌幅 {stock.get('change_pct', 0):.2f}% 超跌反弹"
            })
        
        return signals
    
    def should_sell(self, position: Dict, current_quote: Dict) -> bool:
        """
        判断是否应该卖出
        
        Args:
            position: 持仓信息
            current_quote: 当前行情
        
        Returns:
            是否卖出
        """
        # 如果反弹超过 5%，止盈
        if current_quote.get("change_pct", 0) > 5:
            return True
        
        # 如果继续下跌超过 3%，止损
        if current_quote.get("change_pct", 0) < -3:
            return True
        
        return False


# 测试代码
if __name__ == "__main__":
    # 模拟行情数据
    test_quotes = [
        {"symbol": "NVDA", "price": 174.0, "change_pct": 5.38, "market": "US"},
        {"symbol": "TSLA", "price": 372.0, "change_pct": 4.82, "market": "US"},
        {"symbol": "BABA", "price": 125.0, "change_pct": 2.5, "market": "US"},
        {"symbol": "BIDU", "price": 110.0, "change_pct": -1.5, "market": "US"},
        {"symbol": "00100.HK", "price": 920.0, "change_pct": -8.0, "market": "HK"},
        {"symbol": "06869.HK", "price": 180.0, "change_pct": -7.5, "market": "HK"},
        {"symbol": "02513.HK", "price": 690.0, "change_pct": -5.5, "market": "HK"},
    ]
    
    strategy = MeanReversionStrategy(top_n=3, max_drop_pct=-3.0)
    signals = strategy.generate_signals(test_quotes)
    
    print("均值回归策略信号:")
    for signal in signals:
        print(f"  {signal['action']} {signal['symbol']}: {signal['reason']}")
