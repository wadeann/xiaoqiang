#!/usr/bin/env python3
"""
小强量化系统 - 优化策略回测
改进版多因子策略：趋势过滤 + 严格选股
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
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.run_backtest import DataLoader


class EnhancedFactorAnalyzer:
    """增强因子分析器"""
    
    def calculate_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算多因子"""
        df = df.copy()
        
        # 确保数值列
        for col in ['open', 'close', 'high', 'low', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 1. 动量因子
        df['return_5d'] = df['close'].pct_change(5) * 100
        df['return_10d'] = df['close'].pct_change(10) * 100
        df['return_20d'] = df['close'].pct_change(20) * 100
        
        # 2. 相对强度因子 (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-6)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. 均线系统
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # 均线多头排列
        df['ma_bullish'] = ((df['ma5'] > df['ma10']) & 
                            (df['ma10'] > df['ma20']) & 
                            (df['close'] > df['ma5'])).astype(int)
        
        # 4. 成交量因子
        df['volume_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma5'] * 100
        df['volume_trend'] = (df['volume_ma5'] > df['volume_ma20']).astype(int)
        
        # 5. 波动率因子
        df['volatility'] = df['close'].pct_change().rolling(20).std() * 100
        df['volatility_rank'] = df['volatility'].rolling(60).rank(pct=True)
        
        # 6. 价格位置
        df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / \
                               (df['high'].rolling(20).max() - df['low'].rolling(20).min() + 1e-6) * 100
        
        # 7. 趋势强度 (ADX 简化版)
        df['trend_strength'] = abs(df['return_5d']) / (df['volatility'] + 1e-6)
        
        # 8. 综合得分 (改进版)
        # 趋势过滤: 必须在 MA20 之上
        df['trend_filter'] = (df['close'] > df['ma20']).astype(int)
        
        # 动量得分
        df['momentum_score'] = (
            df['return_5d'] * 0.3 + 
            df['return_10d'] * 0.2 + 
            df['return_20d'] * 0.1
        )
        
        # 趋势得分
        df['trend_score'] = (
            df['ma_bullish'] * 2 +
            df['trend_filter'] * 1 +
            df['trend_strength'] * 0.5
        )
        
        # 成交量得分
        df['volume_score'] = (
            df['volume_trend'] * 0.5 +
            (df['volume_ratio'] > 100).astype(int) * 0.5
        )
        
        # 风险得分 (波动率越低越好)
        df['risk_score'] = -df['volatility_rank'] * 10
        
        # 最终得分
        df['score'] = (
            df['momentum_score'] * 0.4 +
            df['trend_score'] * 0.3 +
            df['volume_score'] * 0.15 +
            df['risk_score'] * 0.15
        )
        
        # 只在趋势向上时给正分
        df.loc[df['trend_filter'] == 0, 'score'] = -abs(df.loc[df['trend_filter'] == 0, 'score'])
        
        return df


class OptimizedBacktest:
    """优化回测引擎"""
    
    def __init__(self, starting_capital: float = 1000000, 
                 stop_loss: float = -0.08,  # 更严格的止损
                 take_profit: float = 0.15):  # 止盈
        self.starting_capital = starting_capital
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.analyzer = EnhancedFactorAnalyzer()
        self.data_loader = DataLoader()
        self.reset()
    
    def reset(self):
        self.cash = self.starting_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
    
    def load_data(self, symbols: list, days: int = 90) -> dict:
        """加载数据"""
        print(f"📥 加载 {len(symbols)} 只股票, {days} 天历史数据...")
        data = {}
        for symbol in symbols:
            try:
                df = self.data_loader.load_a_share_history(symbol, days=days)
                if df is not None and not df.empty:
                    df = self.analyzer.calculate_factors(df)
                    df['symbol'] = symbol
                    data[symbol] = df
                    print(f"  ✅ {symbol}")
            except Exception as e:
                pass
        return data
    
    def run(self, data: dict, 
            max_positions: int = 5,
            position_size: float = 0.15,
            min_score: float = 0.5,
            min_rsi: float = 40,
            max_rsi: float = 80):
        """运行优化策略"""
        
        print("=" * 70)
        print("📊 优化策略回测")
        print("=" * 70)
        print(f"最大持仓: {max_positions} 只")
        print(f"单只仓位: {position_size*100}%")
        print(f"最低得分: {min_score}")
        print(f"RSI 范围: {min_rsi} - {max_rsi}")
        print(f"止损: {self.stop_loss*100}%")
        print(f"止盈: {self.take_profit*100}%")
        
        # 获取日期列表
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
            
            # 止损检查
            pnl_rate = (equity - self.starting_capital) / self.starting_capital
            if pnl_rate <= self.stop_loss:
                print(f"\n⚠️ {date} 触发止损 ({pnl_rate*100:.2f}%)")
                self._liquidate(daily_bars, date)
                break
            
            # 检查持仓止盈止损
            self._check_positions(daily_bars, date)
            
            # 生成信号
            signals = self._generate_signals(daily_bars, min_score, min_rsi, max_rsi)
            
            # 执行交易
            for signal in signals:
                if signal['action'] == 'BUY' and len(self.positions) < max_positions:
                    self._buy(signal, position_size)
                elif signal['action'] == 'SELL':
                    self._sell(signal, date)
        
        # 清仓
        if self.positions:
            self._liquidate(daily_bars, all_dates[-1])
        
        return self._calc_results()
    
    def _calc_equity(self, daily_bars):
        equity = self.cash
        for symbol, pos in self.positions.items():
            bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
            if bar:
                equity += pos['qty'] * bar['close']
        return equity
    
    def _check_positions(self, daily_bars, date):
        """检查持仓止盈止损"""
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
            if not bar:
                continue
            
            pnl_rate = (bar['close'] - pos['avg_price']) / pos['avg_price']
            
            # 个股止损
            if pnl_rate <= -0.08:
                self._sell({'symbol': symbol, 'price': bar['close'], 'reason': '个股止损'}, date)
            # 个股止盈
            elif pnl_rate >= self.take_profit:
                self._sell({'symbol': symbol, 'price': bar['close'], 'reason': '个股止盈'}, date)
    
    def _generate_signals(self, daily_bars, min_score, min_rsi, max_rsi):
        """生成信号"""
        signals = []
        
        # 按得分排序
        scored = []
        for bar in daily_bars:
            score = bar.get('score', 0)
            rsi = bar.get('rsi', 50)
            trend_filter = bar.get('trend_filter', 0)
            
            # 严格筛选条件
            if (score >= min_score and 
                min_rsi <= rsi <= max_rsi and 
                trend_filter == 1):
                scored.append((bar['symbol'], score, bar['close'], bar))
        
        # 买入信号
        scored.sort(key=lambda x: x[1], reverse=True)
        for symbol, score, price, bar in scored[:5]:
            if symbol not in self.positions:
                signals.append({
                    'action': 'BUY',
                    'symbol': symbol,
                    'price': price,
                    'score': score,
                    'reason': f"得分:{score:.2f}, RSI:{bar.get('rsi', 0):.0f}"
                })
        
        # 卖出信号 (得分转负或趋势破坏)
        for symbol in list(self.positions.keys()):
            bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
            if bar:
                score = bar.get('score', 0)
                trend_filter = bar.get('trend_filter', 0)
                
                if score < -0.3 or trend_filter == 0:
                    signals.append({
                        'action': 'SELL',
                        'symbol': symbol,
                        'price': bar['close'],
                        'reason': f"趋势破坏 (score={score:.2f})"
                    })
        
        return signals
    
    def _buy(self, signal, position_size):
        symbol = signal['symbol']
        price = signal['price']
        
        value = self.cash * position_size
        qty = int(value / price / 100) * 100
        if qty < 100:
            return
        
        cost = qty * price * 1.001  # 佣金
        if cost > self.cash:
            return
        
        self.cash -= cost
        self.positions[symbol] = {
            'qty': qty,
            'avg_price': price * 1.001,
            'cost': cost
        }
        
        self.trades.append({
            'type': 'BUY',
            'symbol': symbol,
            'price': price,
            'qty': qty,
            'value': qty * price,
            'reason': signal.get('reason', '')
        })
    
    def _sell(self, signal, date):
        symbol = signal['symbol']
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        price = signal['price']
        value = pos['qty'] * price * 0.999  # 佣金
        
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
            'reason': signal.get('reason', '')
        })
    
    def _liquidate(self, daily_bars, date):
        for symbol in list(self.positions.keys()):
            bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
            if bar:
                self._sell({'symbol': symbol, 'price': bar['close'], 'reason': '清仓'}, date)
    
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


# 热门板块股票池
STOCKS = [
    # AI/光模块
    "300308.SZ", "300394.SZ", "300502.SZ", "002281.SZ", "688205.SH", "688195.SH",
    # 半导体
    "603501.SH", "002371.SZ", "300661.SZ", "688012.SH", "688120.SH", "688008.SH",
    # 新能源
    "300750.SZ", "002594.SZ", "002812.SZ", "300014.SZ", "601012.SH", "300274.SZ",
    # 消费电子
    "000725.SZ", "002475.SZ", "002241.SZ", "603160.SH",
    # 医药
    "300760.SZ", "300122.SZ", "300015.SZ",
    # 金融科技
    "300033.SZ", "600570.SH",
]


if __name__ == "__main__":
    engine = OptimizedBacktest(
        starting_capital=1000000,
        stop_loss=-0.08,
        take_profit=0.15
    )
    
    # 加载数据
    data = engine.load_data(STOCKS, days=120)
    
    # 运行优化策略
    results = engine.run(
        data,
        max_positions=6,
        position_size=0.12,
        min_score=0.3,
        min_rsi=35,
        max_rsi=75
    )
    
    engine.print_results(results)
    
    # 保存结果
    import json
    from pathlib import Path
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 权益曲线
    eq_df = pd.DataFrame(results['equity_curve'])
    eq_df.to_csv(reports_dir / f"equity_optimized_{ts}.csv", index=False)
    
    # 交易记录
    tr_df = pd.DataFrame(results['trades'])
    tr_df.to_csv(reports_dir / f"trades_optimized_{ts}.csv", index=False)
    
    # 摘要
    summary = {k: v for k, v in results.items() if k not in ['equity_curve', 'trades']}
    with open(reports_dir / f"summary_optimized_{ts}.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📁 报告已保存到 reports/")
