#!/usr/bin/env python3
"""
小强量化系统 - 动量策略 v2.0
支持: 回测模式、止损止盈、持仓管理
"""

from typing import List, Dict, Optional
import pandas as pd
import numpy as np


class MomentumStrategy:
    """动量策略 - 追涨强势股"""
    
    def __init__(self, top_n: int = 3, min_change_pct: float = 3.0,
                 stop_loss: float = -0.08, take_profit: float = 0.15,
                 trailing_stop: float = 0.05):
        """
        初始化
        
        Args:
            top_n: 买入前 N 只标的
            min_change_pct: 最小涨幅阈值 (%)
            stop_loss: 止损比例 (默认 -8%)
            take_profit: 止盈比例 (默认 +15%)
            trailing_stop: 移动止损回撤比例 (默认 5%)
        """
        self.top_n = top_n
        self.min_change_pct = min_change_pct
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trailing_stop = trailing_stop
        
        # 持仓跟踪
        self.position_highs = {}  # {symbol: highest_price}
    
    def generate_signals(self, quotes: List[Dict], positions: Dict = None) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            quotes: 行情数据列表
            positions: 当前持仓 (可选，用于回测)
        
        Returns:
            交易信号列表
        """
        signals = []
        
        # 过滤涨幅大于阈值的标的
        strong_stocks = [q for q in quotes if q.get("change_pct", 0) >= self.min_change_pct]
        
        # 按涨幅排序
        strong_stocks.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
        
        # 取前 N 只
        top_stocks = strong_stocks[:self.top_n]
        
        # 生成买入信号
        for stock in top_stocks:
            signals.append({
                "symbol": stock.get("symbol"),
                "market": stock.get("market", "US"),
                "action": "BUY",
                "change_pct": stock.get("change_pct", 0),
                "price": stock.get("price") or stock.get("close"),
                "reason": f"涨幅 {stock.get('change_pct', 0):.2f}% 超过阈值 {self.min_change_pct}%",
                "date": stock.get("date", "")
            })
        
        # 生成卖出信号 (如果有持仓)
        if positions:
            sell_signals = self._check_sell_signals(quotes, positions)
            signals.extend(sell_signals)
        
        return signals
    
    def _check_sell_signals(self, quotes: List[Dict], positions: Dict) -> List[Dict]:
        """检查卖出信号"""
        sell_signals = []
        
        for symbol, position in positions.items():
            # 查找当前行情
            quote = next((q for q in quotes if q.get("symbol") == symbol), None)
            if not quote:
                continue
            
            current_price = quote.get("price") or quote.get("close")
            avg_price = position.get("avg_price", position.get("total_cost", 0) / position.get("quantity", 1))
            
            if avg_price <= 0:
                continue
            
            pnl_rate = (current_price - avg_price) / avg_price
            
            # 更新最高价
            if symbol not in self.position_highs:
                self.position_highs[symbol] = current_price
            else:
                self.position_highs[symbol] = max(self.position_highs[symbol], current_price)
            
            highest_price = self.position_highs[symbol]
            
            # 止损
            if pnl_rate <= self.stop_loss:
                sell_signals.append({
                    "symbol": symbol,
                    "action": "SELL",
                    "price": current_price,
                    "reason": f"止损: 亏损 {pnl_rate*100:.2f}% 超过阈值 {self.stop_loss*100}%",
                    "date": quote.get("date", "")
                })
            
            # 止盈
            elif pnl_rate >= self.take_profit:
                sell_signals.append({
                    "symbol": symbol,
                    "action": "SELL",
                    "price": current_price,
                    "reason": f"止盈: 盈利 {pnl_rate*100:.2f}% 达到目标 {self.take_profit*100}%",
                    "date": quote.get("date", "")
                })
            
            # 移动止损
            elif current_price < highest_price * (1 - self.trailing_stop):
                sell_signals.append({
                    "symbol": symbol,
                    "action": "SELL",
                    "price": current_price,
                    "reason": f"移动止损: 从高点回撤 {(1 - current_price/highest_price)*100:.2f}%",
                    "date": quote.get("date", "")
                })
        
        return sell_signals
    
    def reset(self):
        """重置策略状态"""
        self.position_highs = {}


class MomentumStrategyV2:
    """动量策略 V2 - 支持多因子"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            "top_n": 3,
            "min_change_pct": 3.0,
            "min_volume": 1000000,  # 最小成交额
            "min_turnover": 2.0,    # 最小换手率
            "stop_loss": -0.08,
            "take_profit": 0.15,
            "trailing_stop": 0.05,
        }
        
        self.position_highs = {}
    
    def score_stock(self, quote: Dict) -> float:
        """
        计算股票得分
        
        Args:
            quote: 行情数据
        
        Returns:
            得分 (0-100)
        """
        score = 0
        
        # 涨幅得分 (最高 40 分)
        change = quote.get("change_pct", 0)
        if change > 10:
            score += 40
        elif change > 5:
            score += 30
        elif change > 3:
            score += 20
        elif change > 0:
            score += 10
        
        # 成交额得分 (最高 30 分)
        amount = quote.get("amount", 0) or quote.get("volume", 0) * quote.get("price", 1)
        if amount > 100000000:
            score += 30
        elif amount > 50000000:
            score += 20
        elif amount > 10000000:
            score += 10
        
        # 换手率得分 (最高 30 分)
        turnover = quote.get("turnover", 0)
        if turnover > 10:
            score += 30
        elif turnover > 5:
            score += 20
        elif turnover > 2:
            score += 10
        
        return score
    
    def generate_signals(self, quotes: List[Dict], positions: Dict = None) -> List[Dict]:
        """生成交易信号"""
        signals = []
        
        # 计算得分并排序
        scored_stocks = []
        for q in quotes:
            score = self.score_stock(q)
            if score >= 40 and q.get("change_pct", 0) >= self.config["min_change_pct"]:
                scored_stocks.append((q, score))
        
        scored_stocks.sort(key=lambda x: x[1], reverse=True)
        
        # 取前 N 只
        top_n = self.config["top_n"]
        for stock, score in scored_stocks[:top_n]:
            signals.append({
                "symbol": stock.get("symbol"),
                "market": stock.get("market", "US"),
                "action": "BUY",
                "change_pct": stock.get("change_pct", 0),
                "price": stock.get("price") or stock.get("close"),
                "score": score,
                "reason": f"综合得分 {score} 分，涨幅 {stock.get('change_pct', 0):.2f}%",
                "date": stock.get("date", "")
            })
        
        # 卖出信号
        if positions:
            for symbol, position in positions.items():
                quote = next((q for q in quotes if q.get("symbol") == symbol), None)
                if not quote:
                    continue
                
                current_price = quote.get("price") or quote.get("close")
                avg_price = position.get("avg_price", 0)
                
                if avg_price <= 0:
                    continue
                
                pnl_rate = (current_price - avg_price) / avg_price
                
                # 更新最高价
                if symbol not in self.position_highs:
                    self.position_highs[symbol] = current_price
                else:
                    self.position_highs[symbol] = max(self.position_highs[symbol], current_price)
                
                highest_price = self.position_highs[symbol]
                
                # 止损
                if pnl_rate <= self.config["stop_loss"]:
                    signals.append({
                        "symbol": symbol,
                        "action": "SELL",
                        "price": current_price,
                        "reason": f"止损: {pnl_rate*100:.2f}%",
                        "date": quote.get("date", "")
                    })
                
                # 止盈
                elif pnl_rate >= self.config["take_profit"]:
                    signals.append({
                        "symbol": symbol,
                        "action": "SELL",
                        "price": current_price,
                        "reason": f"止盈: {pnl_rate*100:.2f}%",
                        "date": quote.get("date", "")
                    })
                
                # 移动止损
                elif current_price < highest_price * (1 - self.config["trailing_stop"]):
                    signals.append({
                        "symbol": symbol,
                        "action": "SELL",
                        "price": current_price,
                        "reason": f"移动止损: 回撤 {(1 - current_price/highest_price)*100:.2f}%",
                        "date": quote.get("date", "")
                    })
        
        return signals
    
    def reset(self):
        """重置策略状态"""
        self.position_highs = {}


# 测试代码
if __name__ == "__main__":
    # 模拟行情数据
    test_quotes = [
        {"symbol": "688205.SH", "price": 244.98, "change_pct": 18.92, "volume": 5000000, "turnover": 8.5},
        {"symbol": "688195.SH", "price": 331.63, "change_pct": 16.66, "volume": 3000000, "turnover": 6.2},
        {"symbol": "688307.SH", "price": 87.68, "change_pct": 13.93, "volume": 2000000, "turnover": 4.5},
        {"symbol": "002281.SZ", "price": 90.88, "change_pct": 8.32, "volume": 8000000, "turnover": 12.3},
        {"symbol": "300308.SZ", "price": 616.00, "change_pct": 5.84, "volume": 10000000, "turnover": 5.1},
        {"symbol": "300750.SZ", "price": 180.0, "change_pct": -3.5, "volume": 15000000, "turnover": 3.2},
    ]
    
    print("=" * 60)
    print("动量策略 V1 测试")
    print("=" * 60)
    strategy_v1 = MomentumStrategy(top_n=3, min_change_pct=3.0)
    signals_v1 = strategy_v1.generate_signals(test_quotes)
    for s in signals_v1:
        print(f"  {s['action']} {s['symbol']}: {s['reason']}")
    
    print("\n" + "=" * 60)
    print("动量策略 V2 测试 (多因子)")
    print("=" * 60)
    strategy_v2 = MomentumStrategyV2()
    signals_v2 = strategy_v2.generate_signals(test_quotes)
    for s in signals_v2:
        print(f"  {s['action']} {s['symbol']}: {s['reason']} (得分: {s.get('score', 0)})")
