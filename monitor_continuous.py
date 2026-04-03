#!/usr/bin/env python3
"""
小强量化系统 - 持续监控模式
"""

import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.a_share_data import AShareDataSource
from data.realtime_fetcher import RealtimeFetcher
from data.rockflow_config import API_KEY
from strategies.momentum import MomentumStrategy
from strategies.risk_manager import RiskManager
from executor.trader import Trader


class ContinuousMonitor:
    """持续监控器"""
    
    def __init__(self, interval: int = 60):
        self.interval = interval
        self.a_share = AShareDataSource(timeout=10, retry=3)
        self.us_fetcher = RealtimeFetcher(API_KEY)
        self.momentum = MomentumStrategy(top_n=3, min_change_pct=3.0)
        self.risk = RiskManager()
        self.trader = Trader(API_KEY)
    
    def clear_screen(self):
        """清屏"""
        print("\033[2J\033[H", end="")
    
    def get_us_quotes(self):
        """获取美股行情"""
        try:
            quotes = self.us_fetcher.scan_all()
            return quotes
        except:
            return {}
    
    def get_a_share_quotes(self):
        """获取A股行情"""
        try:
            return self.a_share.get_ai_stocks_quotes()
        except:
            return {}
    
    def analyze_and_signal(self):
        """分析并生成信号"""
        # A股信号
        a_quotes = self.get_a_share_quotes()
        a_list = []
        for code, q in a_quotes.items():
            if q and q.get('price', 0) > 0:
                price = q['price']
                pre_close = q.get('pre_close', 1)
                change = ((price - pre_close) / pre_close * 100) if pre_close else 0
                a_list.append({
                    'symbol': code,
                    'name': q.get('name', ''),
                    'market': 'SH' if code.startswith('sh') else 'SZ',
                    'price': price,
                    'change_pct': change
                })
        
        a_signals = self.momentum.generate_signals(a_list)
        
        # 美股信号
        us_quotes = self.get_us_quotes()
        us_list = []
        for symbol, q in us_quotes.items():
            us_list.append({
                'symbol': symbol,
                'market': q.get('market', 'US'),
                'price': q.get('price'),
                'change_pct': q.get('change_pct', 0)
            })
        
        us_signals = self.momentum.generate_signals(us_list)
        
        return a_signals, us_signals
    
    def run(self):
        """运行监控"""
        print("🐉 小强量化系统 - 持续监控模式")
        print(f"刷新间隔: {self.interval} 秒")
        print("按 Ctrl+C 退出")
        print()
        
        try:
            iteration = 0
            while True:
                iteration += 1
                
                # 清屏
                self.clear_screen()
                
                # 标题
                print("=" * 70)
                print("🐉 小强量化系统 - 持续监控")
                print("=" * 70)
                print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"轮次: {iteration}")
                print("=" * 70)
                
                # A股市场
                print("\n📊 A股市场概况")
                print("-" * 70)
                indices = self.a_share.get_index_quotes()
                for code, q in indices.items():
                    if q and q.get('price', 0) > 0:
                        price = q['price']
                        pre = q.get('pre_close', 1)
                        change = ((price - pre) / pre * 100) if pre else 0
                        emoji = "📈" if change > 0 else ("📉" if change < 0 else "➡️")
                        print(f"{emoji} {q.get('name', code)}: {price:.2f} ({change:+.2f}%)")
                
                # A股 AI 板块
                print("\n🤖 A股 AI/半导体板块")
                print("-" * 70)
                a_quotes = self.get_a_share_quotes()
                a_sorted = sorted(
                    [(k, v) for k, v in a_quotes.items() if v and v.get('price', 0) > 0],
                    key=lambda x: ((x[1]['price'] - x[1].get('pre_close', 1)) / x[1].get('pre_close', 1) * 100) if x[1].get('pre_close', 1) else 0,
                    reverse=True
                )
                for i, (code, q) in enumerate(a_sorted[:5], 1):
                    price = q['price']
                    pre = q.get('pre_close', 1)
                    change = ((price - pre) / pre * 100) if pre else 0
                    emoji = "🔥" if change > 3 else ("📈" if change > 0 else "📉")
                    print(f"{i}. {emoji} {q.get('name', code)}: {price:.2f} ({change:+.2f}%)")
                
                # 美股 AI 板块
                print("\n🇺🇸 美股 AI 板块 (待成交订单)")
                print("-" * 70)
                us_quotes = self.get_us_quotes()
                for symbol in ['NBIS', 'CRWV', 'ARM']:
                    if symbol in us_quotes:
                        q = us_quotes[symbol]
                        price = q.get('price', 0)
                        change = q.get('change_pct', 0)
                        emoji = "🔥" if change > 10 else ("📈" if change > 0 else "📉")
                        print(f"{emoji} {symbol}: ${price:.2f} ({change:+.2f}%)")
                
                # 买卖信号
                print("\n🎯 买卖信号")
                print("-" * 70)
                a_signals, us_signals = self.analyze_and_signal()
                
                print("A股推荐:")
                if a_signals:
                    for s in a_signals[:3]:
                        print(f"  ✅ {s.get('symbol', '')} {s.get('name', '')}: {s.get('reason', '')}")
                else:
                    print("  暂无信号")
                
                print("\n美股推荐:")
                if us_signals:
                    for s in us_signals[:3]:
                        print(f"  ✅ {s.get('symbol', '')}: {s.get('reason', '')}")
                else:
                    print("  暂无信号")
                
                # 风控检查
                print("\n⚠️ 风控状态")
                print("-" * 70)
                account = self.trader.get_account()
                if account:
                    pnl = account['total'] - 1000000
                    pnl_rate = (pnl / 1000000) * 100
                    status = "🟢 正常" if pnl_rate > -10 else "🔴 警告"
                    print(f"  总资产: ${account['total']:,.2f}")
                    print(f"  收益: ${pnl:,.2f} ({pnl_rate:+.2f}%)")
                    print(f"  状态: {status}")
                
                print("\n" + "=" * 70)
                print(f"下次刷新: {self.interval} 秒后 | 按 Ctrl+C 退出")
                print("=" * 70)
                
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            print("\n\n监控已停止")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="小强量化系统 - 持续监控")
    parser.add_argument("--interval", type=int, default=60, help="刷新间隔 (秒)")
    
    args = parser.parse_args()
    
    monitor = ContinuousMonitor(interval=args.interval)
    monitor.run()
