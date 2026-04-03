#!/usr/bin/env python3
"""
小强量化系统 - 监控看板
实时显示账户状态、持仓、盈亏
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional


class Dashboard:
    """监控看板"""
    
    def __init__(self, trader, fetcher):
        """
        初始化
        
        Args:
            trader: 交易执行器
            fetcher: 数据获取器
        """
        self.trader = trader
        self.fetcher = fetcher
    
    def display(self):
        """显示看板"""
        # 清屏
        print("\033[2J\033[H", end="")
        
        # 标题
        print("=" * 70)
        print("🐉 小强量化系统 - 监控看板")
        print("=" * 70)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # 账户信息
        account = self.trader.get_account()
        if account:
            print("\n📊 账户状态")
            print("-" * 70)
            print(f"  总资产: ${account['total']:,.2f}")
            print(f"  现金: ${account['cash']:,.2f}")
            print(f"  购买力: ${account['buying_power']:,.2f}")
            
            # 计算盈亏
            starting_capital = 1000000
            pnl = account['total'] - starting_capital
            pnl_rate = (pnl / starting_capital) * 100
            
            pnl_str = f"${pnl:,.2f}"
            pnl_rate_str = f"{pnl_rate:+.2f}%"
            
            if pnl >= 0:
                print(f"  收益: {pnl_str} ({pnl_rate_str}) ✅")
            else:
                print(f"  收益: {pnl_str} ({pnl_rate_str}) ❌")
            
            # 目标和止损
            print(f"  目标: +100%")
            print(f"  止损: -10%")
            
            if pnl_rate >= 100:
                print("\n  🎯 恭喜！达成目标收益！")
            elif pnl_rate <= -10:
                print("\n  ⚠️ 触发止损线！")
        
        # 持仓信息
        positions = self.trader.get_positions()
        print(f"\n📈 持仓 ({len(positions)} 只)")
        print("-" * 70)
        
        if positions:
            for pos in positions:
                symbol = pos.get("symbol", "N/A")
                quantity = pos.get("quantity", 0)
                avg_cost = pos.get("avgCost", 0)
                market_value = pos.get("marketValue", 0)
                
                print(f"  {symbol}: {quantity}股 @ ${avg_cost:.2f} (市值 ${market_value:,.0f})")
        else:
            print("  空仓")
        
        # 待成交订单
        orders = self.trader.get_pending_orders()
        print(f"\n⏳ 待成交订单 ({len(orders)} 个)")
        print("-" * 70)
        
        if orders:
            for order in orders:
                symbol = order.get("symbol", "N/A")
                quantity = order.get("quantity", 0)
                status = order.get("orderStatus", "UNKNOWN")
                
                print(f"  {symbol}: {quantity}股 [{status}]")
        else:
            print("  无")
        
        # Top 5 涨幅
        print("\n🔥 Top 5 涨幅")
        print("-" * 70)
        
        quotes = self.fetcher.scan_all()
        sorted_quotes = sorted(quotes.items(), key=lambda x: x[1].get("change_pct", 0), reverse=True)
        
        for i, (symbol, quote) in enumerate(sorted_quotes[:5], 1):
            price = quote.get("price", 0)
            change_pct = quote.get("change_pct", 0)
            
            emoji = "🔥" if change_pct > 10 else ("📈" if change_pct > 5 else "📊")
            
            print(f"  {i}. {symbol}: ${price:.2f} ({change_pct:+.2f}%) {emoji}")
        
        # 交易统计
        summary = self.trader.get_trade_summary()
        print(f"\n📋 交易统计")
        print("-" * 70)
        print(f"  总交易次数: {summary['total_trades']}")
        print(f"  买入次数: {summary['buy_trades']}")
        print(f"  卖出次数: {summary['sell_trades']}")
        
        print("=" * 70)
    
    def run(self, interval: int = 60):
        """
        运行监控
        
        Args:
            interval: 刷新间隔 (秒)
        """
        print("启动监控看板...")
        print(f"刷新间隔: {interval} 秒")
        print("按 Ctrl+C 退出")
        print()
        
        try:
            while True:
                self.display()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n监控已停止")


# 测试代码
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from executor.trader import Trader
    from data.realtime_fetcher import RealtimeFetcher
    from data.rockflow_config import API_KEY
    
    trader = Trader(API_KEY)
    fetcher = RealtimeFetcher(API_KEY)
    
    dashboard = Dashboard(trader, fetcher)
    
    # 显示一次
    dashboard.display()
