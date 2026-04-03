#!/usr/bin/env python3
"""
华尔街之狼扫描器 - 每20分钟扫描一次大盘
捕捉所有买入机会，不放过任何机会！
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
from strategies.mean_reversion import MeanReversionStrategy
from executor.trader import Trader


class WallStreetWolf:
    """华尔街之狼扫描器"""
    
    def __init__(self, interval: int = 1200):  # 20分钟 = 1200秒
        self.interval = interval
        self.a_share = AShareDataSource(timeout=10, retry=3)
        self.us_fetcher = RealtimeFetcher(API_KEY)
        self.momentum = MomentumStrategy(top_n=5, min_change_pct=3.0)
        self.mean_reversion = MeanReversionStrategy(top_n=3, max_drop_pct=-3.0)
        self.trader = Trader(API_KEY)
        self.scan_count = 0
    
    def clear_screen(self):
        """清屏"""
        print("\033[2J\033[H", end="")
    
    def get_us_quotes(self):
        """获取美股行情"""
        try:
            return self.us_fetcher.scan_all()
        except:
            return {}
    
    def get_a_share_quotes(self):
        """获取A股行情"""
        try:
            return self.a_share.get_ai_stocks_quotes()
        except:
            return {}
    
    def analyze_market(self):
        """分析市场"""
        results = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'a_share': {},
            'us': {},
            'signals': []
        }
        
        # A股分析
        a_quotes = self.get_a_share_quotes()
        a_list = []
        for code, q in a_quotes.items():
            if q and q.get('price', 0) > 0:
                price = q['price']
                pre = q.get('pre_close', 1)
                change = ((price - pre) / pre * 100) if pre else 0
                a_list.append({
                    'symbol': code,
                    'name': q.get('name', ''),
                    'market': 'SH' if code.startswith('sh') else 'SZ',
                    'price': price,
                    'change_pct': change
                })
        
        # 排序
        a_sorted = sorted(a_list, key=lambda x: x['change_pct'], reverse=True)
        results['a_share']['top_gainers'] = a_sorted[:5]
        results['a_share']['top_losers'] = a_sorted[-3:] if len(a_sorted) > 3 else []
        
        # A股信号
        a_momentum = self.momentum.generate_signals(a_list)
        a_reversion = self.mean_reversion.generate_signals(a_list)
        
        for s in a_momentum:
            s['strategy'] = '动量策略'
            s['market'] = 'A股'
            results['signals'].append(s)
        
        for s in a_reversion:
            s['strategy'] = '均值回归'
            s['market'] = 'A股'
            results['signals'].append(s)
        
        # 美股分析
        us_quotes = self.get_us_quotes()
        us_list = []
        for symbol, q in us_quotes.items():
            us_list.append({
                'symbol': symbol,
                'market': 'US',
                'price': q.get('price'),
                'change_pct': q.get('change_pct', 0)
            })
        
        us_sorted = sorted(us_list, key=lambda x: x['change_pct'], reverse=True)
        results['us']['top_gainers'] = us_sorted[:5]
        results['us']['top_losers'] = us_sorted[-3:] if len(us_sorted) > 3 else []
        
        # 美股信号
        us_momentum = self.momentum.generate_signals(us_list)
        for s in us_momentum:
            s['strategy'] = '动量策略'
            s['market'] = '美股'
            results['signals'].append(s)
        
        return results
    
    def display_report(self, results):
        """显示报告"""
        self.clear_screen()
        
        print("=" * 70)
        print("🐺 华尔街之狼扫描器")
        print("=" * 70)
        print(f"时间: {results['timestamp']}")
        print(f"扫描轮次: {self.scan_count}")
        print("=" * 70)
        
        # A股市场
        print("\n🇨🇳 A股市场")
        print("-" * 70)
        
        # A股指数
        indices = self.a_share.get_index_quotes()
        for code, q in indices.items():
            if q and q.get('price', 0) > 0:
                price = q['price']
                pre = q.get('pre_close', 1)
                change = ((price - pre) / pre * 100) if pre else 0
                emoji = "📈" if change > 0 else ("📉" if change < 0 else "➡️")
                print(f"{emoji} {q.get('name', code)}: {price:.2f} ({change:+.2f}%)")
        
        # A股涨幅榜
        print("\n🔥 A股涨幅榜 Top 5")
        print("-" * 70)
        for i, stock in enumerate(results['a_share'].get('top_gainers', []), 1):
            emoji = "🔥" if stock['change_pct'] > 5 else ("📈" if stock['change_pct'] > 0 else "📉")
            name = stock.get('name', stock['symbol'])
            print(f"{i}. {emoji} {name}: {stock['price']:.2f} ({stock['change_pct']:+.2f}%)")
        
        # 美股市场
        print("\n🇺🇸 美股市场")
        print("-" * 70)
        print("🔥 美股涨幅榜 Top 5")
        for i, stock in enumerate(results['us'].get('top_gainers', []), 1):
            emoji = "🔥" if stock['change_pct'] > 10 else ("📈" if stock['change_pct'] > 0 else "📉")
            print(f"{i}. {emoji} {stock['symbol']}: ${stock['price']:.2f} ({stock['change_pct']:+.2f}%)")
        
        # 交易信号
        print("\n🎯 交易信号")
        print("-" * 70)
        
        signals = results['signals']
        if signals:
            # 按涨幅排序
            signals_sorted = sorted(signals, key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
            
            print("买入推荐:")
            for s in signals_sorted[:8]:
                market = s.get('market', '')
                symbol = s.get('symbol', '')
                name = s.get('name', '')
                change = s.get('change_pct', 0)
                strategy = s.get('strategy', '')
                reason = s.get('reason', '')
                
                if change > 0:
                    emoji = "🔥" if change > 5 else "📈"
                else:
                    emoji = "❄️" if change < -5 else "📉"
                
                print(f"  {emoji} [{market}] {symbol} {name}: {change:+.2f}% | {strategy}")
        else:
            print("  暂无信号")
        
        # 账户状态
        print("\n💰 账户状态")
        print("-" * 70)
        account = self.trader.get_account()
        if account:
            pnl = account['total'] - 1000000
            pnl_rate = (pnl / 1000000) * 100
            status = "🟢 正常" if pnl_rate > -10 else "🔴 警告"
            print(f"总资产: ${account['total']:,.2f}")
            print(f"收益: ${pnl:,.2f} ({pnl_rate:+.2f}%)")
            print(f"状态: {status}")
        
        # 待成交订单
        orders = self.trader.get_pending_orders()
        if orders:
            print(f"\n⏳ 待成交订单: {len(orders)} 个")
            for o in orders[:3]:
                print(f"  - {o.get('symbol', '')}: {o.get('quantity', 0)}股")
        
        print("\n" + "=" * 70)
        print(f"下次扫描: {self.interval // 60} 分钟后 | 按 Ctrl+C 退出")
        print("=" * 70)
    
    def run(self):
        """运行扫描器"""
        print("🐺 华尔街之狼扫描器启动")
        print(f"扫描间隔: {self.interval // 60} 分钟")
        print("按 Ctrl+C 退出")
        print()
        
        try:
            while True:
                self.scan_count += 1
                
                # 分析市场
                results = self.analyze_market()
                
                # 显示报告
                self.display_report(results)
                
                # 保存日志
                self.save_log(results)
                
                # 等待下次扫描
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            print("\n\n扫描已停止")
    
    def save_log(self, results):
        """保存日志"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"wolf_scan_{datetime.now().strftime('%Y%m%d')}.log"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{results['timestamp']}] 扫描轮次 {self.scan_count}\n")
            
            if results['signals']:
                f.write("交易信号:\n")
                for s in results['signals'][:5]:
                    f.write(f"  {s.get('market', '')} {s.get('symbol', '')}: {s.get('change_pct', 0):+.2f}%\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="华尔街之狼扫描器")
    parser.add_argument("--interval", type=int, default=1200, help="扫描间隔 (秒), 默认20分钟")
    
    args = parser.parse_args()
    
    wolf = WallStreetWolf(interval=args.interval)
    wolf.run()
