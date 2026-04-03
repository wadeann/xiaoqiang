#!/usr/bin/env python3
"""
小强量化系统 - 模拟交易系统
跟踪假设买入的股票，模拟交易全过程
目标：100%收益
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from data.a_share_data import AShareDataFetcher
from data.realtime_fetcher import RealtimeFetcher
from data.rockflow_config import API_KEY

sys.path.insert(0, str(Path(__file__).parent))


class SimulatedTrader:
    """模拟交易系统"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {symbol: {quantity, avg_cost, buy_date}}
        self.trades = []  # 交易记录
        self.fetcher_a = AShareDataFetcher()
        self.fetcher_us = RealtimeFetcher(API_KEY) if API_KEY else None
        
        self.history_file = Path(__file__).parent / "watchlist" / "simulated_trades.json"
        self.load_history()
    
    def load_history(self):
        """加载历史数据"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.cash = data.get('cash', self.initial_capital)
                self.positions = data.get('positions', {})
                self.trades = data.get('trades', [])
    
    def save_history(self):
        """保存数据"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions': self.positions,
            'trades': self.trades,
            'last_update': datetime.now().isoformat(),
        }
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def buy(self, symbol: str, market: str, quantity: int, reason: str = ""):
        """模拟买入"""
        if market == "A":
            quotes = self.fetcher_a.scan_all([symbol])
        else:
            quotes = self.fetcher_us.scan_all([symbol])
        
        if symbol not in quotes:
            print(f"❌ 无法获取 {symbol} 行情")
            return False
        
        price = quotes[symbol].get('price', 0)
        cost = price * quantity
        
        if cost > self.cash:
            print(f"❌ 资金不足: 需要 {cost:.2f}, 现金 {self.cash:.2f}")
            return False
        
        # 执行买入
        self.cash -= cost
        
        if symbol in self.positions:
            # 加仓
            old_qty = self.positions[symbol]['quantity']
            old_cost = self.positions[symbol]['avg_cost']
            new_qty = old_qty + quantity
            new_avg = (old_cost * old_qty + price * quantity) / new_qty
            self.positions[symbol] = {
                'quantity': new_qty,
                'avg_cost': new_avg,
                'buy_date': self.positions[symbol]['buy_date'],
                'market': market,
            }
        else:
            # 新建仓位
            self.positions[symbol] = {
                'quantity': quantity,
                'avg_cost': price,
                'buy_date': datetime.now().strftime('%Y-%m-%d'),
                'market': market,
            }
        
        # 记录交易
        self.trades.append({
            'type': 'BUY',
            'symbol': symbol,
            'market': market,
            'price': price,
            'quantity': quantity,
            'cost': cost,
            'reason': reason,
            'time': datetime.now().isoformat(),
        })
        
        self.save_history()
        
        print(f"✅ 买入 {symbol}: {quantity}股 @ ¥{price:.2f}, 成本 ¥{cost:.2f}")
        print(f"   原因: {reason}")
        print(f"   剩余现金: ¥{self.cash:.2f}")
        
        return True
    
    def sell(self, symbol: str, quantity: int = None, reason: str = ""):
        """模拟卖出"""
        if symbol not in self.positions:
            print(f"❌ 没有持有 {symbol}")
            return False
        
        if quantity is None or quantity > self.positions[symbol]['quantity']:
            quantity = self.positions[symbol]['quantity']
        
        market = self.positions[symbol].get('market', 'A')
        
        if market == "A":
            quotes = self.fetcher_a.scan_all([symbol])
        else:
            quotes = self.fetcher_us.scan_all([symbol])
        
        if symbol not in quotes:
            print(f"❌ 无法获取 {symbol} 行情")
            return False
        
        price = quotes[symbol].get('price', 0)
        revenue = price * quantity
        avg_cost = self.positions[symbol]['avg_cost']
        profit = (price - avg_cost) * quantity
        profit_pct = (price - avg_cost) / avg_cost * 100
        
        # 执行卖出
        self.cash += revenue
        
        self.positions[symbol]['quantity'] -= quantity
        if self.positions[symbol]['quantity'] <= 0:
            del self.positions[symbol]
        
        # 记录交易
        self.trades.append({
            'type': 'SELL',
            'symbol': symbol,
            'market': market,
            'price': price,
            'quantity': quantity,
            'revenue': revenue,
            'profit': profit,
            'profit_pct': profit_pct,
            'reason': reason,
            'time': datetime.now().isoformat(),
        })
        
        self.save_history()
        
        emoji = "🟢" if profit > 0 else "🔴"
        print(f"✅ 卖出 {symbol}: {quantity}股 @ ¥{price:.2f}, 收入 ¥{revenue:.2f}")
        print(f"   {emoji} 盈亏: ¥{profit:.2f} ({profit_pct:+.2f}%)")
        print(f"   原因: {reason}")
        print(f"   当前现金: ¥{self.cash:.2f}")
        
        return True
    
    def get_portfolio_value(self) -> float:
        """计算总资产"""
        total = self.cash
        
        for symbol, pos in self.positions.items():
            market = pos.get('market', 'A')
            quantity = pos['quantity']
            
            if market == "A":
                quotes = self.fetcher_a.scan_all([symbol])
            else:
                quotes = self.fetcher_us.scan_all([symbol])
            
            if symbol in quotes:
                price = quotes[symbol].get('price', 0)
                total += price * quantity
        
        return total
    
    def get_performance(self) -> Dict:
        """计算业绩"""
        total = self.get_portfolio_value()
        profit = total - self.initial_capital
        profit_pct = profit / self.initial_capital * 100
        
        return {
            'initial_capital': self.initial_capital,
            'current_value': total,
            'cash': self.cash,
            'profit': profit,
            'profit_pct': profit_pct,
            'positions_count': len(self.positions),
            'trades_count': len(self.trades),
            'days': len(set(t['time'][:10] for t in self.trades)) if self.trades else 0,
        }
    
    def report(self):
        """生成报告"""
        perf = self.get_performance()
        
        print("\n" + "=" * 70)
        print("📊 模拟交易报告")
        print("=" * 70)
        print(f"初始资金: ¥{perf['initial_capital']:,.2f}")
        print(f"当前资产: ¥{perf['current_value']:,.2f}")
        print(f"现金余额: ¥{perf['cash']:,.2f}")
        print(f"持仓数量: {perf['positions_count']} 只")
        
        emoji = "🟢" if perf['profit'] > 0 else "🔴"
        print(f"\n{emoji} 总收益: ¥{perf['profit']:,.2f} ({perf['profit_pct']:+.2f}%)")
        print(f"目标收益: 100% (还差 {100 - perf['profit_pct']:.2f}%)")
        
        # 持仓明细
        if self.positions:
            print("\n📈 持仓明细:")
            for symbol, pos in self.positions.items():
                market = pos.get('market', 'A')
                quantity = pos['quantity']
                avg_cost = pos['avg_cost']
                buy_date = pos.get('buy_date', '')
                
                if market == "A":
                    quotes = self.fetcher_a.scan_all([symbol])
                else:
                    quotes = self.fetcher_us.scan_all([symbol])
                
                if symbol in quotes:
                    price = quotes[symbol].get('price', 0)
                    change = quotes[symbol].get('change_pct', 0)
                    profit = (price - avg_cost) * quantity
                    profit_pct = (price - avg_cost) / avg_cost * 100
                    emoji = "🟢" if profit > 0 else "🔴"
                    
                    print(f"  {emoji} {symbol}: {quantity}股")
                    print(f"     成本: ¥{avg_cost:.2f} → 现价: ¥{price:.2f}")
                    print(f"     盈亏: ¥{profit:.2f} ({profit_pct:+.2f}%)")
                    print(f"     买入日期: {buy_date}")
        
        # 交易统计
        if self.trades:
            buy_count = len([t for t in self.trades if t['type'] == 'BUY'])
            sell_count = len([t for t in self.trades if t['type'] == 'SELL'])
            
            print(f"\n📊 交易统计:")
            print(f"  买入次数: {buy_count}")
            print(f"  卖出次数: {sell_count}")
            
            # 计算胜率
            sells = [t for t in self.trades if t['type'] == 'SELL']
            if sells:
                wins = len([t for t in sells if t['profit'] > 0])
                win_rate = wins / len(sells) * 100
                print(f"  胜率: {win_rate:.1f}% ({wins}/{len(sells)})")
                
                avg_profit = sum(t['profit'] for t in sells) / len(sells)
                print(f"  平均盈利: ¥{avg_profit:.2f}")
        
        print("\n" + "=" * 70)
        
        return perf


def test_simulation():
    """测试模拟交易"""
    print("=" * 70)
    print("🎮 模拟交易系统测试")
    print("=" * 70)
    print("目标: 100%收益")
    print("初始资金: ¥100,000")
    print()
    
    trader = SimulatedTrader(initial_capital=100000)
    
    # 显示当前状态
    trader.report()
    
    # 模拟买入（示例）
    print("\n💡 建议操作:")
    print("  1. 基于今日油气板块强势，可买入杰瑞股份、中曼石油")
    print("  2. 设置止损 -5%，止盈 +10%")
    print("  3. 分批建仓，每只股票最多 30% 仓位")
    
    return trader


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="模拟交易系统")
    parser.add_argument("--buy", nargs=3, metavar=('SYMBOL', 'MARKET', 'QUANTITY'), help="买入股票")
    parser.add_argument("--sell", nargs=2, metavar=('SYMBOL', 'QUANTITY'), help="卖出股票")
    parser.add_argument("--report", action="store_true", help="查看报告")
    parser.add_argument("--test", action="store_true", help="测试模式")
    
    args = parser.parse_args()
    
    trader = SimulatedTrader(initial_capital=100000)
    
    if args.buy:
        symbol, market, quantity = args.buy
        trader.buy(symbol, market.upper(), int(quantity), "手动买入")
    elif args.sell:
        symbol, quantity = args.sell
        trader.sell(symbol, int(quantity), "手动卖出")
    elif args.report:
        trader.report()
    elif args.test:
        test_simulation()
    else:
        trader.report()
