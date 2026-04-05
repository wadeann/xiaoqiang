"""
200%年收益策略回测验证 v2 - 简化版
"""

import sys
sys.path.append('/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang')

from datetime import datetime
from strategies.aggressive_200pct_v2 import (
    DragonStrategy, RocketStrategy, SectorRotationStrategy,
    AggressiveConfig, STRATEGY_CONFIGS
)
from trading_strategy.models import OHLCVBar, Signal, SignalType
from trading_strategy.utils.data_generator import generate_sample_bars


class SimpleBacktest:
    """简化回测引擎"""
    
    def __init__(self, strategy, config):
        self.strategy = strategy
        self.config = config
    
    def run(self, bars, initial_capital=1000000):
        """运行回测"""
        
        cash = initial_capital
        position = None  # {'quantity': 0, 'entry_price': 0, 'highest': 0, 'entry_date': None}
        trades = []
        
        for i, bar in enumerate(bars):
            self.strategy.update(bar)
            
            # 持仓检查
            if position and position['quantity'] > 0:
                current_price = bar.close
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                
                # 更新最高价
                if current_price > position['highest']:
                    position['highest'] = current_price
                
                # 止损
                if pnl_pct <= self.config.stop_loss:
                    cash += position['quantity'] * current_price
                    trades.append({
                        'pnl_pct': pnl_pct,
                        'reason': '止损'
                    })
                    position = None
                
                # 第一止盈
                elif pnl_pct >= self.config.take_profit_1 and not position.get('tp1'):
                    sell_qty = position['quantity'] * 0.5
                    cash += sell_qty * current_price
                    position['quantity'] -= sell_qty
                    position['tp1'] = True
                    trades.append({
                        'pnl_pct': pnl_pct,
                        'reason': '第一止盈'
                    })
                
                # 第二止盈
                elif pnl_pct >= self.config.take_profit_2:
                    cash += position['quantity'] * current_price
                    trades.append({
                        'pnl_pct': pnl_pct,
                        'reason': '第二止盈'
                    })
                    position = None
                
                # 移动止损
                elif current_price <= position['highest'] * (1 - self.config.trailing_stop):
                    cash += position['quantity'] * current_price
                    trades.append({
                        'pnl_pct': pnl_pct,
                        'reason': '移动止损'
                    })
                    position = None
                
                # 时间止损
                elif position['entry_date'] and (bar.timestamp - position['entry_date']).days >= self.config.max_hold_days:
                    cash += position['quantity'] * current_price
                    trades.append({
                        'pnl_pct': pnl_pct,
                        'reason': '时间止损'
                    })
                    position = None
            
            # 买入信号检查
            else:
                signal = self.strategy.generate_signal(bar)
                
                if signal.signal_type == SignalType.BUY and signal.strength >= self.config.min_strength:
                    buy_value = cash * self.config.position_size
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
        total_return = (final_value - initial_capital) / initial_capital
        days = len(bars)
        annual_return = total_return * (252 / days) if days > 0 else 0
        
        wins = [t for t in trades if t['pnl_pct'] > 0]
        win_rate = len(wins) / len(trades) if trades else 0
        
        return {
            'initial': initial_capital,
            'final': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'trades': len(trades),
            'win_rate': win_rate
        }


def main():
    print("=" * 60)
    print("🎯 200%年收益策略回测验证")
    print("=" * 60)
    
    # 生成测试数据
    print("\n📊 生成测试数据...")
    bars = generate_sample_bars(
        start_date=datetime(2025, 10, 1),
        num_bars=180,
        initial_price=100.0,
        volatility=0.03,
        trend=0.002,
        seed=42
    )
    print(f"✓ 生成 {len(bars)} 天数据")
    
    # 测试每套策略
    results = {}
    config = AggressiveConfig()
    
    for key, cfg in STRATEGY_CONFIGS.items():
        print(f"\n{'='*60}")
        print(f"📈 策略: {cfg['name']}")
        print(f"{'='*60}")
        
        strategy = cfg['strategy'](config)
        backtest = SimpleBacktest(strategy, config)
        result = backtest.run(bars)
        
        results[key] = result
        
        print(f"起始资金: ¥{result['initial']:,.0f}")
        print(f"最终权益: ¥{result['final']:,.0f}")
        print(f"总收益率: {result['total_return']*100:.2f}%")
        print(f"年化收益: {result['annual_return']*100:.2f}%")
        print(f"交易次数: {result['trades']}")
        print(f"胜率: {result['win_rate']*100:.2f}%")
        
        # 目标检查
        target = cfg['target']
        if result['annual_return'] >= target:
            print(f"✅ 达到目标 ({target*100:.0f}%年化)")
        else:
            gap = target - result['annual_return']
            print(f"⚠️ 未达目标，差距: {gap*100:.2f}%")
    
    # 最佳策略
    best = max(results.items(), key=lambda x: x[1]['annual_return'])
    
    print("\n" + "=" * 60)
    print("🏆 最佳策略")
    print("=" * 60)
    print(f"策略: {STRATEGY_CONFIGS[best[0]]['name']}")
    print(f"年化收益: {best[1]['annual_return']*100:.2f}%")
    print(f"总收益: {best[1]['total_return']*100:.2f}%")
    
    return results


if __name__ == "__main__":
    main()