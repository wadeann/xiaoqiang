#!/usr/bin/env python3
"""
小强量化系统 - 自动交易决策引擎
整合模拟交易和实盘交易，自动决策买卖
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from data.a_share_data import AShareDataFetcher
from data.realtime_fetcher import RealtimeFetcher
from data.rockflow_config import API_KEY, BASE_URL
from data.rockflow_adapter import RockflowAdapter


class AutoTrader:
    """自动交易决策引擎"""
    
    def __init__(self):
        self.a_fetcher = AShareDataFetcher()
        self.us_fetcher = RealtimeFetcher(API_KEY) if API_KEY else None
        self.us_adapter = RockflowAdapter(API_KEY, BASE_URL) if API_KEY else None
        
        # 模拟交易文件
        self.sim_file = Path(__file__).parent / "watchlist" / "simulated_trades.json"
        
        # 交易配置
        self.config = {
            'a_share': {
                'initial_capital': 100000,
                'max_position_pct': 0.3,  # 单只最大30%
                'stop_loss_pct': -0.05,    # 止损 -5%
                'take_profit_pct': 0.10,   # 止盈 +10%
                'buy_threshold': 3.0,      # 买入阈值：涨幅>3%
                'sell_threshold': -3.0,    # 卖出阈值：跌幅<-3%
            },
            'us_share': {
                'initial_capital': 1000000,  # $1M
                'max_position_pct': 0.3,
                'stop_loss_pct': -0.10,       # 止损 -10%
                'take_profit_pct': 0.20,      # 止盈 +20%
                'buy_threshold': 4.0,
                'sell_threshold': -5.0,
            }
        }
        
        self.load_portfolio()
    
    def load_portfolio(self):
        """加载持仓数据"""
        if self.sim_file.exists():
            with open(self.sim_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.a_positions = data.get('a_positions', {})
                self.us_positions = data.get('us_positions', {})
                self.a_cash = data.get('a_cash', self.config['a_share']['initial_capital'])
                self.us_cash = data.get('us_cash', self.config['us_share']['initial_capital'])
                self.trades = data.get('trades', [])
        else:
            self.a_positions = {}
            self.us_positions = {}
            self.a_cash = self.config['a_share']['initial_capital']
            self.us_cash = self.config['us_share']['initial_capital']
            self.trades = []
    
    def save_portfolio(self):
        """保存持仓数据"""
        self.sim_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'a_cash': self.a_cash,
            'us_cash': self.us_cash,
            'a_positions': self.a_positions,
            'us_positions': self.us_positions,
            'trades': self.trades,
            'last_update': datetime.now().isoformat(),
        }
        with open(self.sim_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def analyze_a_share(self) -> Dict:
        """分析A股市场，生成交易信号"""
        print("\n" + "=" * 70)
        print("📊 A股市场分析")
        print("=" * 70)
        
        # 热门板块股票池
        watchlist = {
            "油气": ["002353.SZ", "603619.SH", "600028.SH", "601857.SH", "601808.SH"],
            "创新药": ["603259.SH", "300760.SZ", "002821.SZ", "688180.SH"],
            "军工": ["600893.SH", "002179.SZ"],
            "AI算力": ["300474.SZ", "688256.SH", "002230.SZ"],
            "半导体": ["688981.SH", "002049.SZ", "603501.SH"],
        }
        
        # 获取所有股票行情
        all_symbols = []
        for symbols in watchlist.values():
            all_symbols.extend(symbols)
        
        quotes = self.a_fetcher.scan_all(all_symbols)
        
        # 分析信号
        buy_signals = []
        sell_signals = []
        
        for symbol, quote in quotes.items():
            change = quote.get('change_pct', 0)
            name = quote.get('name', '')
            
            # 买入信号
            if change > self.config['a_share']['buy_threshold']:
                buy_signals.append({
                    'symbol': symbol,
                    'name': name,
                    'change': change,
                    'price': quote.get('price', 0),
                    'reason': f"涨幅{change:.1f}%超过阈值{self.config['a_share']['buy_threshold']}%"
                })
            
            # 卖出信号（检查持仓）
            if symbol in self.a_positions:
                pos = self.a_positions[symbol]
                avg_cost = pos['avg_cost']
                current_price = quote.get('price', 0)
                pnl_pct = (current_price - avg_cost) / avg_cost
                
                # 止损
                if pnl_pct < self.config['a_share']['stop_loss_pct']:
                    sell_signals.append({
                        'symbol': symbol,
                        'name': name,
                        'price': current_price,
                        'pnl_pct': pnl_pct,
                        'reason': f"触发止损{pnl_pct:.1f}%<{self.config['a_share']['stop_loss_pct']*100}%"
                    })
                
                # 止盈
                elif pnl_pct > self.config['a_share']['take_profit_pct']:
                    sell_signals.append({
                        'symbol': symbol,
                        'name': name,
                        'price': current_price,
                        'pnl_pct': pnl_pct,
                        'reason': f"触发止盈{pnl_pct:.1f}%>{self.config['a_share']['take_profit_pct']*100}%"
                    })
        
        # 排序
        buy_signals.sort(key=lambda x: x['change'], reverse=True)
        
        # 输出
        print("\n🟢 买入信号:")
        if buy_signals:
            for i, s in enumerate(buy_signals[:5], 1):
                print(f"  {i}. {s['name']}({s['symbol']}): {s['change']:+.2f}% - {s['reason']}")
        else:
            print("  无")
        
        print("\n🔴 卖出信号:")
        if sell_signals:
            for i, s in enumerate(sell_signals, 1):
                print(f"  {i}. {s['name']}({s['symbol']}): {s['pnl_pct']:+.2f}% - {s['reason']}")
        else:
            print("  无")
        
        return {
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'quotes': quotes,
        }
    
    def execute_trades(self, analysis: Dict):
        """执行交易"""
        print("\n" + "=" * 70)
        print("💰 执行交易")
        print("=" * 70)
        
        # 执行卖出
        for signal in analysis['sell_signals']:
            symbol = signal['symbol']
            if symbol in self.a_positions:
                pos = self.a_positions[symbol]
                quantity = pos['quantity']
                price = signal['price']
                revenue = price * quantity
                avg_cost = pos['avg_cost']
                profit = (price - avg_cost) * quantity
                
                # 执行卖出
                self.a_cash += revenue
                del self.a_positions[symbol]
                
                # 记录
                self.trades.append({
                    'type': 'SELL',
                    'market': 'A',
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'revenue': revenue,
                    'profit': profit,
                    'pnl_pct': signal['pnl_pct'],
                    'reason': signal['reason'],
                    'time': datetime.now().isoformat(),
                })
                
                emoji = "🟢" if profit > 0 else "🔴"
                print(f"{emoji} 卖出 {symbol}: {quantity}股 @ ¥{price:.2f}")
                print(f"   收入: ¥{revenue:.2f}, 盈亏: ¥{profit:.2f} ({signal['pnl_pct']:+.2f}%)")
                print(f"   原因: {signal['reason']}")
        
        # 执行买入（按信号强度和仓位限制）
        for signal in analysis['buy_signals'][:3]:  # 最多买入3只
            symbol = signal['symbol']
            price = signal['price']
            
            # 检查是否已持有
            if symbol in self.a_positions:
                print(f"⚪ 跳过 {symbol}: 已持有")
                continue
            
            # 计算仓位
            position_size = self.a_cash * self.config['a_share']['max_position_pct']
            quantity = int(position_size / price)
            
            if quantity < 100:
                print(f"⚪ 跳过 {symbol}: 资金不足")
                continue
            
            # 检查现金
            cost = price * quantity
            if cost > self.a_cash:
                quantity = int(self.a_cash / price / 100) * 100
                cost = price * quantity
            
            # 执行买入
            self.a_cash -= cost
            self.a_positions[symbol] = {
                'quantity': quantity,
                'avg_cost': price,
                'buy_date': datetime.now().strftime('%Y-%m-%d'),
                'market': 'A',
            }
            
            # 记录
            self.trades.append({
                'type': 'BUY',
                'market': 'A',
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'cost': cost,
                'reason': signal['reason'],
                'time': datetime.now().isoformat(),
            })
            
            print(f"🟢 买入 {symbol}: {quantity}股 @ ¥{price:.2f}")
            print(f"   成本: ¥{cost:.2f}")
            print(f"   原因: {signal['reason']}")
        
        # 保存
        self.save_portfolio()
        
        return self.get_report()
    
    def get_report(self) -> Dict:
        """生成报告"""
        # A股资产
        a_value = self.a_cash
        for symbol, pos in self.a_positions.items():
            quotes = self.a_fetcher.scan_all([symbol])
            if symbol in quotes:
                price = quotes[symbol].get('price', 0)
                a_value += price * pos['quantity']
        
        # 美股资产（如果有API）
        us_value = self.us_cash
        if self.us_adapter:
            assets = self.us_adapter.get_assets()
            if assets:
                us_value = assets.get('total', self.us_cash)
        
        # 总资产
        total_value = a_value + us_value * 7.2  # 美元转人民币
        
        # 计算收益
        a_profit = a_value - self.config['a_share']['initial_capital']
        a_profit_pct = a_profit / self.config['a_share']['initial_capital'] * 100
        
        us_profit = us_value - self.config['us_share']['initial_capital']
        us_profit_pct = us_profit / self.config['us_share']['initial_capital'] * 100
        
        return {
            'a_cash': self.a_cash,
            'a_positions': self.a_positions,
            'a_value': a_value,
            'a_profit': a_profit,
            'a_profit_pct': a_profit_pct,
            'us_cash': self.us_cash,
            'us_positions': self.us_positions,
            'us_value': us_value,
            'us_profit': us_profit,
            'us_profit_pct': us_profit_pct,
            'total_value': total_value,
        }
    
    def run(self):
        """运行自动交易"""
        # 1. 分析市场
        analysis = self.analyze_a_share()
        
        # 2. 执行交易
        report = self.execute_trades(analysis)
        
        # 3. 输出报告
        print("\n" + "=" * 70)
        print("📊 账户状态")
        print("=" * 70)
        print(f"A股:")
        print(f"  现金: ¥{report['a_cash']:,.2f}")
        print(f"  持仓: {len(report['a_positions'])}只")
        print(f"  资产: ¥{report['a_value']:,.2f}")
        emoji_a = "🟢" if report['a_profit'] > 0 else "🔴"
        print(f"  收益: {emoji_a} ¥{report['a_profit']:,.2f} ({report['a_profit_pct']:+.2f}%)")
        
        print(f"\n美股:")
        print(f"  现金: ${report['us_cash']:,.2f}")
        print(f"  持仓: {len(report['us_positions'])}只")
        print(f"  资产: ${report['us_value']:,.2f}")
        emoji_us = "🟢" if report['us_profit'] > 0 else "🔴"
        print(f"  收益: {emoji_us} ${report['us_profit']:,.2f} ({report['us_profit_pct']:+.2f}%)")
        
        print(f"\n总资产: ¥{report['total_value']:,.2f}")
        print("=" * 70)
        
        return report


if __name__ == "__main__":
    trader = AutoTrader()
    trader.run()
