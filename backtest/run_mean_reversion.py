#!/usr/bin/env python3
"""
小强量化系统 - 均值回归策略
适用于震荡市场，提升胜率
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


class MeanReversionStrategy:
    """均值回归策略 - 震荡市高胜率"""
    
    def __init__(self, starting_capital=1000000):
        self.starting_capital = starting_capital
        self.reset()
    
    def reset(self):
        self.cash = self.starting_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.entry_prices = {}
    
    def calculate_indicators(self, df):
        """计算均值回归指标"""
        df = df.copy()
        
        for col in ['close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 布林带
        df['ma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['upper_band'] = df['ma20'] + 2 * df['std20']
        df['lower_band'] = df['ma20'] - 2 * df['std20']
        df['band_width'] = (df['upper_band'] - df['lower_band']) / df['ma20']
        
        # 价格位置 (相对于布林带)
        df['bb_position'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'] + 1e-6)
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-6)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 威廉指标
        df['williams'] = (df['high'].rolling(14).max() - df['close']) / (df['high'].rolling(14).max() - df['low'].rolling(14).min() + 1e-6) * -100
        
        # 成交量
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 动量
        df['momentum'] = df['close'].pct_change(5) * 100
        
        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(20).std() * 100
        
        # 买卖信号
        df['oversold'] = (
            (df['bb_position'] < 0.2) &  # 接近下轨
            (df['rsi'] < 35) &  # RSI 超卖
            (df['williams'] < -80)  # 威廉超卖
        ).astype(int)
        
        df['overbought'] = (
            (df['bb_position'] > 0.8) &  # 接近上轨
            (df['rsi'] > 65)  # RSI 超买
        ).astype(int)
        
        # 综合得分 (负值表示超卖，正值表示超买)
        df['score'] = (
            (0.5 - df['bb_position']) * 2 +  # 布林带位置
            (50 - df['rsi']) / 50  # RSI 位置
        )
        
        return df
    
    def load_data(self, symbols, days=120):
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
            max_positions=6,
            position_size=0.12,
            oversold_threshold=-0.5,
            overbought_threshold=0.5,
            stop_loss=-0.06,
            take_profit=0.08):
        """
        运行均值回归策略
        
        参数:
            oversold_threshold: 超卖阈值 (负值，越小越超卖)
            overbought_threshold: 超买阈值 (正值，越大越超买)
        """
        print("=" * 70)
        print("📊 均值回归策略 (震荡市高胜率)")
        print("=" * 70)
        print(f"最大持仓: {max_positions} 只")
        print(f"单只仓位: {position_size*100}%")
        print(f"超卖阈值: {oversold_threshold}")
        print(f"超买阈值: {overbought_threshold}")
        print(f"止损: {stop_loss*100}%")
        print(f"止盈: {take_profit*100}%")
        
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
        for date in all_dates:
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
                
                pnl_rate = (bar['close'] - pos['avg_price']) / pos['avg_price']
                
                # 卖出条件
                sell_reason = None
                
                # 止损
                if pnl_rate <= stop_loss:
                    sell_reason = f"止损 ({pnl_rate*100:.1f}%)"
                
                # 止盈
                elif pnl_rate >= take_profit:
                    sell_reason = f"止盈 ({pnl_rate*100:.1f}%)"
                
                # 回归均值 (超买)
                elif bar.get('score', 0) > overbought_threshold:
                    sell_reason = f"均值回归 (得分={bar.get('score', 0):.2f})"
                
                # 超买信号
                elif bar.get('overbought', 0) == 1:
                    sell_reason = "超买信号"
                
                if sell_reason:
                    self._sell(symbol, bar['close'], date, sell_reason)
            
            # 买入信号 - 寻找超卖股票
            if len(self.positions) < max_positions:
                signals = []
                for bar in daily_bars:
                    score = bar.get('score', 0)
                    oversold = bar.get('oversold', 0)
                    
                    # 超卖条件
                    if score < oversold_threshold or oversold == 1:
                        if bar['symbol'] not in self.positions:
                            signals.append((bar['symbol'], score, bar['close'], bar))
                
                # 按得分排序 (越负越优先)
                signals.sort(key=lambda x: x[1])
                
                for symbol, score, price, bar in signals[:max_positions - len(self.positions)]:
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
        self.entry_prices[symbol] = price
        
        self.trades.append({
            'type': 'BUY',
            'symbol': symbol,
            'price': price,
            'qty': qty,
            'value': qty * price,
            'score': bar.get('score', 0),
            'rsi': bar.get('rsi', 0),
            'bb_position': bar.get('bb_position', 0)
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
        if symbol in self.entry_prices:
            del self.entry_prices[symbol]
        
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


# 股票池
STOCKS = [
    # 光模块
    "300308.SZ", "300394.SZ", "300502.SZ", "002281.SZ", "688205.SH", "688195.SH",
    # 半导体
    "603501.SH", "002371.SZ", "300661.SZ", "688012.SH", "688120.SH", "688008.SH",
    # 新能源
    "300750.SZ", "002594.SZ", "002812.SZ", "300014.SZ", "601012.SH", "300274.SZ",
    # 消费电子
    "000725.SZ", "002475.SZ", "002241.SZ", "603160.SH",
    # 医药
    "300760.SZ", "300122.SZ", "300015.SZ",
    # 金融
    "300033.SZ", "600570.SH", "601166.SH", "600036.SH",
]


if __name__ == "__main__":
    strategy = MeanReversionStrategy(starting_capital=1000000)
    data = strategy.load_data(STOCKS, days=120)
    
    results = strategy.run(
        data,
        max_positions=6,
        position_size=0.12,
        oversold_threshold=-0.5,
        overbought_threshold=0.5,
        stop_loss=-0.06,
        take_profit=0.08
    )
    
    strategy.print_results(results)
    
    # 分析
    sells = [t for t in results['trades'] if t['type'] == 'SELL']
    wins = [t for t in sells if t.get('pnl', 0) > 0]
    
    print(f"\n📊 盈利交易: {len(wins)} 笔")
    print(f"📊 亏损交易: {len(sells) - len(wins)} 笔")
    
    from collections import Counter
    reasons = Counter([t.get('reason', '') for t in sells])
    print("\n卖出原因:")
    for reason, count in reasons.most_common():
        avg_pnl = np.mean([t['pnl'] for t in sells if t.get('reason') == reason])
        print(f"  {reason}: {count} 笔, 平均盈亏 ¥{avg_pnl:,.0f}")
