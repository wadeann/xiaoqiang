"""
最强动量股测试 - 腾景科技、德科立、中际旭创
使用400天历史数据回测
"""

import sys
sys.path.append('/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang')

import os
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from strategies.aggressive_200pct_v2 import RocketStrategy, DragonStrategy
from trading_strategy.models import OHLCVBar, Signal, SignalType


@dataclass
class OptimizedConfig:
    """优化版配置"""
    position_size: float = 0.40
    stop_loss: float = -0.08
    take_profit_1: float = 0.25
    take_profit_2: float = 0.50
    trailing_stop: float = 0.12
    max_hold_days: int = 10
    min_strength: float = 0.3


class OptimizedRocket(RocketStrategy):
    """优化版火箭策略"""
    
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        if len(self._bars) < 5:
            return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="数据不足")
        
        start_price = self._bars[-3].close
        pct_change = (bar.close - start_price) / start_price
        
        volumes = [b.volume for b in self._bars[-3:]]
        volume_expanding = volumes[-1] > volumes[-2]
        
        if pct_change > 0.03 and volume_expanding:
            strength = min(1.0, pct_change * 5 + 0.3)
            return Signal(
                SignalType.BUY, bar.timestamp, bar.close, strength,
                f"火箭: 涨幅{pct_change*100:.1f}%, 量增"
            )
        
        return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="未达条件")


def run_backtest(bars, config, strategy_class):
    """运行回测"""
    
    strategy = strategy_class(config)
    
    cash = 1000000
    position = None
    trades = []
    equity_curve = []
    
    for bar in bars:
        strategy.update(bar)
        
        # 记录权益
        current_value = cash
        if position:
            current_value += position['quantity'] * bar.close
        equity_curve.append({
            'date': bar.timestamp,
            'value': current_value
        })
        
        # 持仓检查
        if position and position['quantity'] > 0:
            current_price = bar.close
            pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            
            if current_price > position['highest']:
                position['highest'] = current_price
            
            # 止损
            if pnl_pct <= config.stop_loss:
                cash += position['quantity'] * current_price
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': bar.timestamp,
                    'pnl_pct': pnl_pct,
                    'reason': '止损'
                })
                position = None
            
            # 第一止盈
            elif pnl_pct >= config.take_profit_1 and not position.get('tp1'):
                sell_qty = position['quantity'] * 0.5
                cash += sell_qty * current_price
                position['quantity'] -= sell_qty
                position['tp1'] = True
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': bar.timestamp,
                    'pnl_pct': pnl_pct,
                    'reason': '第一止盈'
                })
            
            # 第二止盈
            elif pnl_pct >= config.take_profit_2:
                cash += position['quantity'] * current_price
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': bar.timestamp,
                    'pnl_pct': pnl_pct,
                    'reason': '第二止盈'
                })
                position = None
            
            # 移动止损
            elif current_price <= position['highest'] * (1 - config.trailing_stop):
                cash += position['quantity'] * current_price
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': bar.timestamp,
                    'pnl_pct': pnl_pct,
                    'reason': '移动止损'
                })
                position = None
        
        # 买入信号
        else:
            signal = strategy.generate_signal(bar)
            
            if signal.signal_type == SignalType.BUY and signal.strength >= config.min_strength:
                buy_value = cash * config.position_size
                quantity = buy_value / bar.close
                cash -= buy_value
                
                position = {
                    'quantity': quantity,
                    'entry_price': bar.close,
                    'highest': bar.close,
                    'entry_date': bar.timestamp,
                    'tp1': False
                }
    
    # 最终价值
    final_value = cash
    if position:
        final_value += position['quantity'] * bars[-1].close
    
    # 统计
    total_return = (final_value - 1000000) / 1000000
    days = len(bars)
    annual_return = total_return * (252 / days) if days > 0 else 0
    
    wins = [t for t in trades if t['pnl_pct'] > 0]
    win_rate = len(wins) / len(trades) if trades else 0
    
    # 计算最大回撤
    values = [e['value'] for e in equity_curve]
    peak = values[0]
    max_drawdown = 0
    for v in values:
        if v > peak:
            peak = v
        drawdown = (peak - v) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return {
        'initial': 1000000,
        'final': final_value,
        'total_return': total_return,
        'annual_return': annual_return,
        'trades': len(trades),
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'equity_curve': equity_curve,
        'trades_detail': trades
    }


def main():
    print("=" * 70)
    print("🔥 最强动量股测试 - 腾景科技、德科立、中际旭创")
    print("=" * 70)
    
    # 最强动量股
    dragon_stocks = {
        '688195.SH': {'name': '腾景科技', 'gain': '+712.6%'},
        '688205.SH': {'name': '德科立', 'gain': '+319.7%'},
        '300308.SZ': {'name': '中际旭创', 'gain': '+318.6%'}
    }
    
    cache_dir = '/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang/data/cache'
    config = OptimizedConfig()
    
    all_results = {}
    
    for symbol, info in dragon_stocks.items():
        data_file = os.path.join(cache_dir, f'{symbol}_400d.csv')
        
        if not os.path.exists(data_file):
            print(f"⚠️ {info['name']} 400天数据不存在")
            continue
        
        print(f"\n{'='*70}")
        print(f"📊 {info['name']} ({symbol}) - 历史涨幅: {info['gain']}")
        print(f"{'='*70}")
        
        # 加载数据
        df = pd.read_csv(data_file)
        bars = []
        for _, row in df.iterrows():
            bar = OHLCVBar(
                timestamp=pd.to_datetime(row.get('date', row.get('timestamp', _))),
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row.get('volume', row.get('amount', 1000000))
            )
            bars.append(bar)
        
        print(f"✓ 加载 {len(bars)} 条K线 ({len(bars)//252}年数据)")
        
        # 运行回测
        result = run_backtest(bars, config, OptimizedRocket)
        
        all_results[symbol] = result
        
        # 打印结果
        print(f"\n📈 火箭策略(优化版) 结果:")
        print(f"  起始资金: ¥{result['initial']:,.0f}")
        print(f"  最终权益: ¥{result['final']:,.0f}")
        print(f"  总收益率: {result['total_return']*100:.2f}%")
        print(f"  年化收益: {result['annual_return']*100:.2f}%")
        print(f"  交易次数: {result['trades']}次")
        print(f"  胜率: {result['win_rate']*100:.1f}%")
        print(f"  最大回撤: {result['max_drawdown']*100:.2f}%")
        
        # 目标检查
        if result['annual_return'] >= 2.0:
            print(f"  ✅ 达到200%年化目标！")
        else:
            gap = 2.0 - result['annual_return']
            print(f"  ⚠️ 距200%目标差距: {gap*100:.2f}%")
    
    # 最佳股票
    best = max(all_results.items(), key=lambda x: x[1]['annual_return'])
    
    print("\n" + "=" * 70)
    print("🏆 最佳动量股")
    print("=" * 70)
    print(f"股票: {dragon_stocks[best[0]]['name']} ({best[0]})")
    print(f"年化收益: {best[1]['annual_return']*100:.2f}%")
    print(f"总收益: {best[1]['total_return']*100:.2f}%")
    print(f"最大回撤: {best[1]['max_drawdown']*100:.2f}%")
    
    # 杠杆策略建议
    print("\n" + "=" * 70)
    print("🎯 杠杆策略建议")
    print("=" * 70)
    
    for leverage in [1.5, 2.0, 2.5, 3.0]:
        leveraged_return = best[1]['annual_return'] * leverage
        leveraged_drawdown = best[1]['max_drawdown'] * leverage
        
        print(f"\n{leverage}x杠杆:")
        print(f"  预期年化收益: {leveraged_return*100:.2f}%", end="")
        
        if leveraged_return >= 2.0:
            print(" ✅ 达标")
        else:
            print()
        
        print(f"  预期最大回撤: {leveraged_drawdown*100:.2f}%")
    
    return all_results


if __name__ == "__main__":
    main()