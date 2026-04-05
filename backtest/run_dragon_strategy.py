#!/usr/bin/env python3
"""
小强量化系统 - 龙头股挖掘与策略优化
目标：筛选翻倍龙头，优化策略达到 100% 收益
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

for proxy in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(proxy, None)

sys.path.insert(0, str(Path(__file__).parent.parent))
from backtest.run_backtest import DataLoader


class DragonStockScanner:
    """龙头股扫描器 - 找出翻倍股"""
    
    def __init__(self):
        self.data_loader = DataLoader()
    
    def scan_all_stocks(self, symbols, days=180):
        """扫描所有股票，找出龙头"""
        print(f"📊 扫描 {len(symbols)} 只股票，筛选龙头...")
        print("=" * 70)
        
        results = []
        
        for symbol in symbols:
            try:
                df = self.data_loader.load_a_share_history(symbol, days=days)
                if df is None or len(df) < days * 0.8:
                    continue
                
                # 计算指标
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                
                # 价格变化
                start_price = df['close'].iloc[0]
                end_price = df['close'].iloc[-1]
                total_return = (end_price - start_price) / start_price * 100
                
                # 最高点涨幅
                max_price = df['close'].max()
                max_return = (max_price - start_price) / start_price * 100
                
                # 回撤
                drawdown = (max_price - end_price) / max_price * 100
                
                # 波动率
                df['returns'] = df['close'].pct_change()
                volatility = df['returns'].std() * np.sqrt(252) * 100
                
                # 成交量趋势
                df['volume_ma'] = df['volume'].rolling(20).mean()
                volume_trend = df['volume'].iloc[-20:].mean() / df['volume_ma'].iloc[-60:].mean()
                
                # 夏普比率
                if df['returns'].std() > 0:
                    sharpe = df['returns'].mean() / df['returns'].std() * np.sqrt(252)
                else:
                    sharpe = 0
                
                # 最大连续上涨
                df['up'] = (df['close'] > df['close'].shift(1)).astype(int)
                max_consecutive_up = 0
                current_up = 0
                for val in df['up']:
                    if val == 1:
                        current_up += 1
                        max_consecutive_up = max(max_consecutive_up, current_up)
                    else:
                        current_up = 0
                
                results.append({
                    'symbol': symbol,
                    'start_price': start_price,
                    'end_price': end_price,
                    'total_return': total_return,
                    'max_return': max_return,
                    'drawdown': drawdown,
                    'volatility': volatility,
                    'volume_trend': volume_trend,
                    'sharpe': sharpe,
                    'max_consecutive_up': max_consecutive_up,
                    'days': len(df)
                })
                
            except Exception as e:
                pass
        
        # 排序
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('total_return', ascending=False)
        
        # 输出结果
        print("\n📈 翻倍股 (>100% 涨幅):")
        print("-" * 70)
        doublers = df_results[df_results['total_return'] > 100]
        for i, row in doublers.iterrows():
            print(f"  {row['symbol']}: +{row['total_return']:.1f}% (最高+{row['max_return']:.1f}%, 夏普{row['sharpe']:.2f})")
        
        print("\n🔥 强势股 (50-100% 涨幅):")
        print("-" * 70)
        strong = df_results[(df_results['total_return'] > 50) & (df_results['total_return'] <= 100)]
        for i, row in strong.iterrows():
            print(f"  {row['symbol']}: +{row['total_return']:.1f}% (最高+{row['max_return']:.1f}%, 夏普{row['sharpe']:.2f})")
        
        print("\n📊 龙头股特征:")
        print("-" * 70)
        if len(doublers) > 0:
            avg_return = doublers['total_return'].mean()
            avg_sharpe = doublers['sharpe'].mean()
            avg_volatility = doublers['volatility'].mean()
            print(f"  平均涨幅: {avg_return:.1f}%")
            print(f"  平均夏普: {avg_sharpe:.2f}")
            print(f"  平均波动率: {avg_volatility:.1f}%")
        
        return df_results


class DragonStrategy:
    """龙头股策略 - 聚焦强势股"""
    
    def __init__(self, starting_capital=1000000):
        self.starting_capital = starting_capital
        self.reset()
    
    def reset(self):
        self.cash = self.starting_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.max_prices = {}
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        df = df.copy()
        
        for col in ['close', 'high', 'low', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # 趋势强度
        df['trend'] = (df['close'] - df['ma20']) / df['ma20'] * 100
        
        # 动量
        df['momentum_5'] = df['close'].pct_change(5) * 100
        df['momentum_10'] = df['close'].pct_change(10) * 100
        df['momentum_20'] = df['close'].pct_change(20) * 100
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-6)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 成交量
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(20).std() * 100
        
        # 强势股得分
        df['strength_score'] = self._calc_strength(df)
        
        return df
    
    def _calc_strength(self, df):
        """计算强势股得分"""
        score = pd.Series(0.0, index=df.index)
        
        # 趋势向上
        trend_up = (df['close'] > df['ma5']) & (df['ma5'] > df['ma10']) & (df['ma10'] > df['ma20'])
        score[trend_up] += 1
        
        # 强势趋势 (价格在 MA20 之上 5% 以上)
        strong_trend = df['trend'] > 5
        score[strong_trend] += 1
        
        # 动量正
        momentum_positive = (df['momentum_5'] > 0) & (df['momentum_10'] > 0)
        score[momentum_positive] += 1
        
        # MACD 金叉
        macd_golden = df['macd_hist'] > 0
        score[macd_golden] += 0.5
        
        # 放量
        volume_up = df['volume_ratio'] > 1.2
        score[volume_up] += 0.5
        
        # RSI 不超买
        rsi_ok = (df['rsi'] > 40) & (df['rsi'] < 80)
        score[rsi_ok] += 0.5
        
        return score
    
    def load_data(self, symbols, days=180):
        """加载数据"""
        print(f"📥 加载 {len(symbols)} 只股票, {days} 天数据...")
        loader = DataLoader()
        data = {}
        for symbol in symbols:
            try:
                df = loader.load_a_share_history(symbol, days=days)
                if df is not None and len(df) >= days * 0.8:
                    df = self.calculate_indicators(df)
                    df['symbol'] = symbol
                    data[symbol] = df
                    print(f"  ✅ {symbol}")
            except:
                pass
        return data
    
    def run(self, data, 
            max_positions=4,
            position_size=0.2,
            min_strength=2.0,
            stop_loss=-0.08,
            take_profit=0.30,
            trailing_stop=0.10):
        """
        龙头股策略
        
        参数:
            max_positions: 最大持仓数
            position_size: 单只仓位
            min_strength: 最低强势得分
            stop_loss: 止损比例
            take_profit: 止盈比例
            trailing_stop: 移动止损比例
        """
        print("=" * 70)
        print("🐉 龙头股策略 - 聚焦强势股")
        print("=" * 70)
        print(f"最大持仓: {max_positions} 只")
        print(f"单只仓位: {position_size*100}%")
        print(f"最低强势得分: {min_strength}")
        print(f"止损: {stop_loss*100}%")
        print(f"止盈: {take_profit*100}%")
        print(f"移动止损: {trailing_stop*100}%")
        
        # 获取日期
        all_dates = set()
        for df in data.values():
            if 'date' in df.columns:
                all_dates.update(df['date'].tolist())
        all_dates = sorted(list(all_dates))
        
        if not all_dates:
            return {"error": "No dates"}
        
        print(f"\n📅 回测期间: {all_dates[0]} ~ {all_dates[-1]} ({len(all_dates)} 天)")
        
        # 逐日回测
        for i, date in enumerate(all_dates):
            # 获取当日数据
            daily_bars = []
            for symbol, df in data.items():
                if 'date' in df.columns and date in df['date'].values:
                    row = df[df['date'] == date].iloc[-1]
                    bar = row.to_dict()
                    bar['symbol'] = symbol
                    daily_bars.append(bar)
            
            if not daily_bars:
                continue
            
            # 计算权益
            equity = self._calc_equity(daily_bars)
            self.equity_curve.append({
                'date': date,
                'equity': equity,
                'positions': len(self.positions)
            })
            
            # 检查持仓
            for symbol in list(self.positions.keys()):
                pos = self.positions[symbol]
                bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
                
                if not bar:
                    continue
                
                # 更新最高价
                if symbol not in self.max_prices:
                    self.max_prices[symbol] = bar['close']
                else:
                    self.max_prices[symbol] = max(self.max_prices[symbol], bar['close'])
                
                pnl_rate = (bar['close'] - pos['avg_price']) / pos['avg_price']
                drawdown = (self.max_prices[symbol] - bar['close']) / self.max_prices[symbol]
                
                # 卖出条件
                sell_reason = None
                
                # 硬止损
                if pnl_rate <= stop_loss:
                    sell_reason = f"止损 ({pnl_rate*100:.1f}%)"
                
                # 移动止损 (盈利后)
                elif pnl_rate > 0.10 and drawdown >= trailing_stop:
                    sell_reason = f"移动止损 (回撤{drawdown*100:.1f}%)"
                
                # 止盈
                elif pnl_rate >= take_profit:
                    sell_reason = f"止盈 ({pnl_rate*100:.1f}%)"
                
                # 强势得分下降
                elif bar.get('strength_score', 0) < 1.0:
                    sell_reason = f"强势减弱 (得分={bar.get('strength_score', 0):.1f})"
                
                if sell_reason:
                    self._sell(symbol, bar['close'], date, sell_reason)
                    if symbol in self.max_prices:
                        del self.max_prices[symbol]
            
            # 买入信号
            if len(self.positions) < max_positions:
                signals = []
                for bar in daily_bars:
                    strength = bar.get('strength_score', 0)
                    if strength >= min_strength and bar['symbol'] not in self.positions:
                        # 强势股：动量强、趋势向上
                        if bar.get('momentum_5', 0) > 2:  # 5日涨幅 > 2%
                            signals.append((bar['symbol'], strength, bar['close'], bar))
                
                # 按强势得分排序
                signals.sort(key=lambda x: x[1], reverse=True)
                
                for symbol, strength, price, bar in signals[:max_positions - len(self.positions)]:
                    self._buy(symbol, price, position_size, bar)
        
        # 清仓
        if self.positions:
            for symbol in list(self.positions.keys()):
                bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
                if bar:
                    self._sell(symbol, bar['close'], all_dates[-1], "期末清仓")
        
        return self._calc_results()
    
    def _calc_equity(self, daily_bars):
        equity = self.cash
        for symbol, pos in self.positions.items():
            bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
            if bar:
                equity += pos['qty'] * bar['close']
        return equity
    
    def _buy(self, symbol, price, position_size, bar):
        value = self.cash * position_size
        qty = int(value / price / 100) * 100
        if qty < 100:
            return
        
        cost = qty * price * 1.001
        if cost > self.cash:
            return
        
        self.cash -= cost
        self.positions[symbol] = {
            'qty': qty,
            'avg_price': price * 1.001,
            'cost': cost
        }
        self.max_prices[symbol] = price
        
        self.trades.append({
            'type': 'BUY',
            'symbol': symbol,
            'price': price,
            'qty': qty,
            'value': qty * price,
            'strength': bar.get('strength_score', 0),
            'momentum': bar.get('momentum_5', 0)
        })
    
    def _sell(self, symbol, price, date, reason):
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        value = pos['qty'] * price * 0.999
        pnl = value - pos['cost']
        pnl_rate = pnl / pos['cost']
        
        self.cash += value
        del self.positions[symbol]
        
        self.trades.append({
            'type': 'SELL',
            'symbol': symbol,
            'price': price,
            'qty': pos['qty'],
            'value': value,
            'pnl': pnl,
            'pnl_rate': pnl_rate,
            'date': date,
            'reason': reason
        })
    
    def _calc_results(self):
        if not self.equity_curve:
            return {"error": "No equity"}
        
        final_equity = self.equity_curve[-1]['equity']
        pnl = final_equity - self.starting_capital
        pnl_rate = pnl / self.starting_capital
        
        # 最大回撤
        max_eq = self.starting_capital
        max_dd = 0
        for rec in self.equity_curve:
            if rec['equity'] > max_eq:
                max_eq = rec['equity']
            dd = (max_eq - rec['equity']) / max_eq
            if dd > max_dd:
                max_dd = dd
        
        # 夏普
        eq_vals = [r['equity'] for r in self.equity_curve]
        returns = [(eq_vals[i] - eq_vals[i-1]) / eq_vals[i-1] for i in range(1, len(eq_vals))]
        sharpe = (np.mean(returns) * 252) / (np.std(returns) * np.sqrt(252)) if returns else 0
        
        # 胜率
        sells = [t for t in self.trades if t['type'] == 'SELL']
        wins = [t for t in sells if t.get('pnl', 0) > 0]
        win_rate = len(wins) / len(sells) if sells else 0
        
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl'] for t in sells if t.get('pnl', 0) < 0]) or 0
        
        return {
            'starting_capital': self.starting_capital,
            'final_equity': final_equity,
            'pnl': pnl,
            'pnl_rate': pnl_rate,
            'pnl_pct': f"{pnl_rate*100:.2f}%",
            'max_drawdown': max_dd,
            'max_drawdown_pct': f"{max_dd*100:.2f}%",
            'sharpe_ratio': sharpe,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'win_rate_pct': f"{win_rate*100:.1f}%",
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss else 0,
            'equity_curve': self.equity_curve,
            'trades': self.trades
        }
    
    def print_results(self, results):
        print("\n" + "=" * 70)
        print("📊 回测结果")
        print("=" * 70)
        print(f"起始资金: ¥{results['starting_capital']:,.0f}")
        print(f"最终权益: ¥{results['final_equity']:,.0f}")
        print(f"总盈亏: ¥{results['pnl']:,.0f} ({results['pnl_pct']})")
        print(f"最大回撤: {results['max_drawdown_pct']}")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"总交易: {results['total_trades']} 次")
        print(f"胜率: {results['win_rate_pct']}")
        print(f"平均盈利: ¥{results['avg_win']:,.0f}")
        print(f"平均亏损: ¥{results['avg_loss']:,.0f}")
        print(f"盈亏比: {results['profit_factor']:.2f}")
        print("=" * 70)


# 扩展龙头股池
DRAGON_STOCKS = [
    # ===== 光模块龙头 (近期最强) =====
    "300308.SZ",  # 中际旭创 - 光模块龙头
    "300394.SZ",  # 天孚通信 - 光器件龙头
    "300502.SZ",  # 新易盛 - 光模块
    "688205.SH",  # 德科立 - 光模块
    "688195.SH",  # 腾景科技 - 光学元件
    "002281.SZ",  # 光迅科技 - 光通信
    "300570.SZ",  # 太辰光 - 光连接器
    "688307.SH",  # 中润光学
    
    # ===== AI芯片 =====
    "300474.SZ",  # 景嘉微
    "688981.SH",  # 中芯国际
    "688256.SH",  # 寒武纪
    "688041.SH",  # 海光信息
    
    # ===== 半导体设备 =====
    "002371.SZ",  # 北方华创
    "688012.SH",  # 中微公司
    "688120.SH",  # 华峰测控
    "688008.SH",  # 澜起科技
    "300661.SZ",  # 圣邦股份
    
    # ===== 新能源 =====
    "300750.SZ",  # 宁德时代
    "002594.SZ",  # 比亚迪
    "002812.SZ",  # 恩捷股份
    "300274.SZ",  # 阳光电源
    "601012.SH",  # 隆基绿能
    "688599.SH",  # 天合光能
    "688303.SH",  # 大全能源
    
    # ===== 机器人 =====
    "300024.SZ",  # 机器人
    "002747.SZ",  # 埃斯顿
    "300124.SZ",  # 汇川技术
    
    # ===== 消费电子 =====
    "002475.SZ",  # 立讯精密
    "000725.SZ",  # 京东方A
    "002241.SZ",  # 歌尔股份
]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', action='store_true', help='扫描龙头股')
    parser.add_argument('--backtest', action='store_true', help='运行回测')
    parser.add_argument('--optimize', action='store_true', help='参数优化')
    args = parser.parse_args()
    
    if args.scan:
        # 扫描龙头股
        scanner = DragonStockScanner()
        results = scanner.scan_all_stocks(DRAGON_STOCKS, days=180)
        
        # 保存结果
        results.to_csv('reports/dragon_stocks_scan.csv', index=False)
        print(f"\n📁 结果已保存到 reports/dragon_stocks_scan.csv")
    
    elif args.optimize:
        # 参数优化
        strategy = DragonStrategy(starting_capital=1000000)
        data = strategy.load_data(DRAGON_STOCKS, days=180)
        
        params_list = [
            {'max_positions': 3, 'position_size': 0.25, 'min_strength': 2.5, 'stop_loss': -0.10, 'take_profit': 0.40, 'trailing_stop': 0.12},
            {'max_positions': 4, 'position_size': 0.20, 'min_strength': 2.0, 'stop_loss': -0.08, 'take_profit': 0.30, 'trailing_stop': 0.10},
            {'max_positions': 5, 'position_size': 0.15, 'min_strength': 1.5, 'stop_loss': -0.08, 'take_profit': 0.25, 'trailing_stop': 0.08},
            {'max_positions': 4, 'position_size': 0.20, 'min_strength': 2.0, 'stop_loss': -0.06, 'take_profit': 0.20, 'trailing_stop': 0.05},
        ]
        
        print("\n" + "=" * 70)
        print("🔧 参数优化 - 目标收益 100%+")
        print("=" * 70)
        
        results = []
        for params in params_list:
            strategy.reset()
            r = strategy.run(data, **params)
            results.append({
                'params': params,
                'pnl_rate': r['pnl_rate'],
                'win_rate': r['win_rate'],
                'sharpe': r['sharpe_ratio'],
                'max_dd': r['max_drawdown'],
            })
            print(f"参数: pos={params['max_positions']}, strength={params['min_strength']}, tp={params['take_profit']}")
            print(f"  收益: {r['pnl_rate']*100:.1f}%, 胜率: {r['win_rate']*100:.1f}%, 夏普: {r['sharpe_ratio']:.2f}, 回撤: {r['max_drawdown']*100:.1f}%")
        
        best = max(results, key=lambda x: x['pnl_rate'])
        print("\n" + "=" * 70)
        print("🏆 最优参数")
        print("=" * 70)
        print(f"参数: {best['params']}")
        print(f"收益: {best['pnl_rate']*100:.1f}%")
        print(f"胜率: {best['win_rate']*100:.1f}%")
        print(f"夏普: {best['sharpe']:.2f}")
    
    else:
        # 默认回测
        strategy = DragonStrategy(starting_capital=1000000)
        data = strategy.load_data(DRAGON_STOCKS, days=180)
        
        results = strategy.run(
            data,
            max_positions=4,
            position_size=0.20,
            min_strength=2.0,
            stop_loss=-0.08,
            take_profit=0.30,
            trailing_stop=0.10
        )
        
        strategy.print_results(results)
