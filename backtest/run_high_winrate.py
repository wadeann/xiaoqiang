#!/usr/bin/env python3
"""
小强量化系统 - 高胜率策略 v2.0
目标：提升胜率到 50%+，收益率到 15%+
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 禁用代理
for proxy in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(proxy, None)

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.run_backtest import DataLoader


class HighWinRateStrategy:
    """高胜率策略 - 更严格的筛选条件"""
    
    def __init__(self, starting_capital=1000000):
        self.starting_capital = starting_capital
        self.reset()
    
    def reset(self):
        self.cash = self.starting_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.entry_dates = {}  # 记录买入日期
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        df = df.copy()
        
        for col in ['open', 'close', 'high', 'low', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 均线系统
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # 多头排列
        df['is_bullish'] = (
            (df['ma5'] > df['ma10']) & 
            (df['ma10'] > df['ma20']) & 
            (df['close'] > df['ma5'])
        ).astype(int)
        
        # 趋势强度
        df['trend_strength'] = (
            (df['close'] - df['ma20']) / df['ma20'] * 100
        )
        
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
        df['volume_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        
        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(20).std() * 100
        
        # 价格位置 (相对于20日高低点)
        df['price_position'] = (
            (df['close'] - df['low'].rolling(20).min()) /
            (df['high'].rolling(20).max() - df['low'].rolling(20).min() + 1e-6)
        )
        
        # 动量
        df['momentum_5'] = df['close'].pct_change(5) * 100
        df['momentum_10'] = df['close'].pct_change(10) * 100
        
        # 综合得分
        df['score'] = self._calculate_score(df)
        
        return df
    
    def _calculate_score(self, df):
        """计算综合得分 - 更严格的条件"""
        score = pd.Series(0.0, index=df.index)
        
        # 1. 趋势条件 (必须满足)
        trend_ok = (
            (df['is_bullish'] == 1) &
            (df['close'] > df['ma20']) &
            (df['ma20'] > df['ma60'].shift(5))  # MA20 在上升
        )
        
        # 2. RSI 条件 (40-65, 避免超买)
        rsi_ok = (df['rsi'] >= 40) & (df['rsi'] <= 65)
        
        # 3. MACD 条件 (金叉或向上)
        macd_ok = (df['macd_hist'] > 0) | (df['macd'] > df['macd'].shift(5))
        
        # 4. 成交量条件 (放量)
        volume_ok = df['volume_ratio'] > 1.0
        
        # 5. 价格位置 (不要买在高点)
        price_ok = df['price_position'] < 0.8
        
        # 6. 动量条件 (正动量但不要太大)
        momentum_ok = (df['momentum_5'] > 0) & (df['momentum_5'] < 15)
        
        # 所有条件必须同时满足
        all_ok = trend_ok & rsi_ok & macd_ok & volume_ok & price_ok & momentum_ok
        
        # 基础得分
        score[all_ok] = 1.0
        
        # 加分项
        score[all_ok & (df['trend_strength'] > 5)] += 0.5  # 强趋势
        score[all_ok & (df['rsi'] < 55)] += 0.3  # RSI 还有空间
        score[all_ok & (df['volume_ratio'] > 1.5)] += 0.3  # 明显放量
        
        # 减分项
        score[all_ok & (df['volatility'] > df['volatility'].rolling(60).quantile(0.7))] -= 0.5  # 高波动
        
        return score
    
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
            except Exception as e:
                pass
        return data
    
    def run(self, data, 
            max_positions=4, 
            position_size=0.18,
            min_score=1.0,
            hold_days=(3, 15),  # 最少/最多持有天数
            stop_loss=-0.06,
            take_profit=0.12,
            trailing_stop=0.05):
        """
        运行策略
        
        参数:
            max_positions: 最大持仓数
            position_size: 单只仓位
            min_score: 最低得分
            hold_days: (最少持有天数, 最多持有天数)
            stop_loss: 止损比例
            take_profit: 止盈比例
            trailing_stop: 移动止损比例
        """
        print("=" * 70)
        print("📊 高胜率策略 v2.0")
        print("=" * 70)
        print(f"最大持仓: {max_positions} 只")
        print(f"单只仓位: {position_size*100}%")
        print(f"最低得分: {min_score}")
        print(f"持有期: {hold_days[0]}-{hold_days[1]} 天")
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
        
        # 记录最高价用于移动止损
        max_prices = {}
        
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
                if symbol not in max_prices:
                    max_prices[symbol] = bar['close']
                else:
                    max_prices[symbol] = max(max_prices[symbol], bar['close'])
                
                # 计算盈亏
                pnl_rate = (bar['close'] - pos['avg_price']) / pos['avg_price']
                
                # 从最高点回撤
                drawdown = (max_prices[symbol] - bar['close']) / max_prices[symbol]
                
                # 持有天数
                hold_day = i - pos.get('entry_idx', i)
                
                # 卖出条件
                sell_reason = None
                
                # 1. 硬止损
                if pnl_rate <= stop_loss:
                    sell_reason = f"止损 ({pnl_rate*100:.1f}%)"
                
                # 2. 移动止损 (盈利后)
                elif pnl_rate > 0.05 and drawdown >= trailing_stop:
                    sell_reason = f"移动止损 (回撤{drawdown*100:.1f}%)"
                
                # 3. 止盈
                elif pnl_rate >= take_profit:
                    sell_reason = f"止盈 ({pnl_rate*100:.1f}%)"
                
                # 4. 最大持有期
                elif hold_day >= hold_days[1]:
                    sell_reason = f"持有期满 ({hold_day}天)"
                
                # 5. 趋势破坏 (持有超过最少天数后)
                elif hold_day >= hold_days[0]:
                    if bar.get('is_bullish', 0) == 0:
                        sell_reason = "趋势破坏"
                    elif bar.get('score', 0) < 0:
                        sell_reason = "得分转负"
                
                if sell_reason:
                    self._sell(symbol, bar['close'], date, sell_reason)
                    if symbol in max_prices:
                        del max_prices[symbol]
            
            # 买入信号
            if len(self.positions) < max_positions:
                signals = []
                for bar in daily_bars:
                    score = bar.get('score', 0)
                    if score >= min_score and bar['symbol'] not in self.positions:
                        signals.append((bar['symbol'], score, bar['close'], bar))
                
                # 按得分排序
                signals.sort(key=lambda x: x[1], reverse=True)
                
                for symbol, score, price, bar in signals[:max_positions - len(self.positions)]:
                    self._buy(symbol, price, position_size, i, bar)
        
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
    
    def _buy(self, symbol, price, position_size, idx, bar):
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
            'cost': cost,
            'entry_idx': idx
        }
        
        self.trades.append({
            'type': 'BUY',
            'symbol': symbol,
            'price': price,
            'qty': qty,
            'value': qty * price,
            'rsi': bar.get('rsi', 0),
            'score': bar.get('score', 0),
            'trend': bar.get('trend_strength', 0)
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
        avg_hold = np.mean([t.get('hold_days', 5) for t in sells]) if sells else 0
        
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


# 精选股票池 - 只选强势板块龙头
SELECTED_STOCKS = [
    # 光模块龙头 (近期最强)
    "300308.SZ",  # 中际旭创
    "300394.SZ",  # 天孚通信
    "300502.SZ",  # 新易盛
    "688205.SH",  # 德科立
    "688195.SH",  # 腾景科技
    
    # 半导体设备
    "002371.SZ",  # 北方华创
    "688012.SH",  # 中微公司
    "688120.SH",  # 华峰测控
    "688008.SH",  # 澜起科技
    
    # 新能源龙头
    "300750.SZ",  # 宁德时代
    "002594.SZ",  # 比亚迪
    "002812.SZ",  # 恩捷股份
    "300274.SZ",  # 阳光电源
    
    # 消费电子
    "002475.SZ",  # 立讯精密
    
    # 医疗器械
    "300760.SZ",  # 迈瑞医疗
]


if __name__ == "__main__":
    strategy = HighWinRateStrategy(starting_capital=1000000)
    
    # 加载数据
    data = strategy.load_data(SELECTED_STOCKS, days=150)
    
    # 运行策略
    results = strategy.run(
        data,
        max_positions=4,
        position_size=0.2,
        min_score=1.0,
        hold_days=(3, 20),
        stop_loss=-0.06,
        take_profit=0.15,
        trailing_stop=0.05
    )
    
    strategy.print_results(results)
    
    # 分析交易
    sells = [t for t in results['trades'] if t['type'] == 'SELL']
    wins = [t for t in sells if t.get('pnl', 0) > 0]
    
    print("\n📊 交易分析:")
    print(f"盈利交易: {len(wins)} 笔")
    print(f"亏损交易: {len(sells) - len(wins)} 笔")
    
    # 按卖出原因统计
    from collections import Counter
    reasons = Counter([t.get('reason', '') for t in sells])
    print("\n卖出原因:")
    for reason, count in reasons.most_common():
        print(f"  {reason}: {count} 笔")
