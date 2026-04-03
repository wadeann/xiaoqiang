#!/usr/bin/env python3
"""
小强量化系统 - 信号过滤器
过滤假信号，提高胜率
"""

from typing import Dict, List, Optional


class SignalFilter:
    """信号过滤器"""
    
    def __init__(self, min_change_pct: float = 3.0, max_change_pct: float = 20.0,
                 min_volume: int = 1000000):
        """
        初始化
        
        Args:
            min_change_pct: 最小涨幅阈值
            max_change_pct: 最大涨幅阈值 (防止追高)
            min_volume: 最小成交量
        """
        self.min_change_pct = min_change_pct
        self.max_change_pct = max_change_pct
        self.min_volume = min_volume
    
    def filter_signals(self, signals: List[Dict], quotes: Dict[str, Dict]) -> List[Dict]:
        """
        过滤信号
        
        Args:
            signals: 原始信号列表
            quotes: 行情数据字典
        
        Returns:
            过滤后的信号列表
        """
        filtered = []
        
        for signal in signals:
            symbol = signal.get("symbol")
            if not symbol:
                continue
            
            quote = quotes.get(symbol, {})
            
            # 检查涨幅范围
            change_pct = signal.get("change_pct", 0)
            if change_pct < self.min_change_pct:
                print(f"  ⚠️ {symbol}: 涨幅 {change_pct:.2f}% < {self.min_change_pct}%，过滤")
                continue
            
            if change_pct > self.max_change_pct:
                print(f"  ⚠️ {symbol}: 涨幅 {change_pct:.2f}% > {self.max_change_pct}%，过滤 (防止追高)")
                continue
            
            # 检查成交量
            volume = quote.get("volume", 0)
            if volume < self.min_volume:
                print(f"  ⚠️ {symbol}: 成交量 {volume:,} < {self.min_volume:,}，过滤")
                continue
            
            # 通过所有过滤
            filtered.append(signal)
        
        return filtered
    
    def check_risk(self, signal: Dict, account: Dict) -> bool:
        """
        检查风险
        
        Args:
            signal: 交易信号
            account: 账户信息
        
        Returns:
            是否通过风险检查
        """
        # 检查现金是否足够
        cash = account.get("cash", 0)
        price = signal.get("price", 0)
        
        if cash < price * 100:  # 至少能买 100 股
            print(f"  ⚠️ 现金不足，无法执行")
            return False
        
        return True
    
    def calculate_position_size(self, signal: Dict, account: Dict,
                                max_position_pct: float = 0.3) -> int:
        """
        计算仓位大小
        
        Args:
            signal: 交易信号
            account: 账户信息
            max_position_pct: 最大仓位比例
        
        Returns:
            股票数量
        """
        total = account.get("total", 0)
        cash = account.get("cash", 0)
        price = signal.get("price", 0)
        
        if price <= 0:
            return 0
        
        # 使用总资产的 max_position_pct 或可用现金，取较小者
        max_value = min(total * max_position_pct, cash * 0.95)
        
        quantity = int(max_value / price)
        
        return max(quantity, 0)


# 测试代码
if __name__ == "__main__":
    # 模拟信号
    signals = [
        {"symbol": "NBIS", "action": "BUY", "change_pct": 13.75, "price": 105.0},
        {"symbol": "CRWV", "action": "BUY", "change_pct": 13.67, "price": 78.5},
        {"symbol": "ARM", "action": "BUY", "change_pct": 11.22, "price": 152.0},
        {"symbol": "NVDA", "action": "BUY", "change_pct": 5.9, "price": 175.0},
        {"symbol": "TSLA", "action": "BUY", "change_pct": 25.0, "price": 375.0},  # 过高，会被过滤
    ]
    
    # 模拟行情
    quotes = {
        "NBIS": {"volume": 5000000},
        "CRWV": {"volume": 3000000},
        "ARM": {"volume": 2000000},
        "NVDA": {"volume": 100000000},
        "TSLA": {"volume": 50000000},
    }
    
    # 模拟账户
    account = {"total": 1000000, "cash": 100000}
    
    # 过滤器
    filter = SignalFilter(min_change_pct=3.0, max_change_pct=20.0, min_volume=1000000)
    
    print("原始信号:")
    for s in signals:
        print(f"  {s['symbol']}: {s['change_pct']:.2f}%")
    
    print("\n过滤后信号:")
    filtered = filter.filter_signals(signals, quotes)
    for s in filtered:
        qty = filter.calculate_position_size(s, account)
        print(f"  {s['symbol']}: {s['change_pct']:.2f}% -> 建议买入 {qty} 股")
