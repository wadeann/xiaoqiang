"""
优化版200%年收益策略 - 放宽参数
"""

import sys
sys.path.append('/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang')

import os
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from strategies.aggressive_200pct_v2 import DragonStrategy, RocketStrategy
from trading_strategy.models import OHLCVBar, Signal, SignalType


@dataclass
class OptimizedConfig:
    """优化版配置 - 放宽条件"""
    position_size: float = 0.40      # 单笔仓位40% (更激进)
    stop_loss: float = -0.08         # 止损-8% (更紧)
    take_profit_1: float = 0.25      # 第一止盈25% (更早)
    take_profit_2: float = 0.50      # 第二止盈50%
    trailing_stop: float = 0.12      # 移动止损12% (更紧)
    max_hold_days: int = 10          # 最长持仓10天 (更快)
    min_strength: float = 0.3        # 最小信号强度0.3 (放宽)


class OptimizedRocket(RocketStrategy):
    """优化版动量火箭 - 放宽条件"""
    
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """生成快速动量信号 - 放宽条件"""
        
        if len(self._bars) < 5:  # 从10降到5
            return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="数据不足")
        
        # 3日涨幅 (从8%降到3%)
        start_price = self._bars[-3].close
        pct_change = (bar.close - start_price) / start_price
        
        # 只检查量放大，不要求连续上涨
        volumes = [b.volume for b in self._bars[-3:]]
        volume_expanding = volumes[-1] > volumes[-2]  # 只检查最后一天
        
        # 放宽条件: 3日涨幅>3% + 量放大
        if pct_change > 0.03 and volume_expanding:
            strength = min(1.0, pct_change * 5 + 0.3)
            return Signal(
                SignalType.BUY, bar.timestamp, bar.close, strength,
                f"火箭(优化): 3日涨幅{pct_change*100:.1f}%, 量增"
            )
        
        return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="未达条件")


from dataclasses import dataclass

class OptimizedDragon(DragonStrategy):
    """优化版龙头捕获 - 放宽条件"""
    
    def generate_signal(self, bar: OHLCVBar) -> Signal:
        """生成买入信号 - 放宽条件"""
        
        if len(self._bars) < 3:  # 从5降到3
            return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="数据不足")
        
        # 3日涨幅 (从15%降到8%)
        start_price = self._bars[-3].close
        pct_change = (bar.close - start_price) / start_price
        
        # 简化RSI计算
        changes = [self._bars[-i].close - self._bars[-i-1].close for i in range(1, min(10, len(self._bars)))]
        gains = [c for c in changes if c > 0]
        losses = [abs(c) for c in changes if c < 0]
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0.001
        rsi = 100 - (100 / (1 + avg_gain/avg_loss))
        
        # 成交量比率 (从2x降到1.5x)
        volumes = [b.volume for b in self._bars[-3:]]
        avg_volume = sum(volumes) / len(volumes)
        volume_ratio = bar.volume / avg_volume if avg_volume > 0 else 1
        
        # MA3 (从MA5简化)
        closes = [b.close for b in self._bars[-3:]]
        ma3 = sum(closes) / len(closes)
        
        # 放宽条件
        if pct_change > 0.08 and 40 <= rsi <= 75 and volume_ratio > 1.5 and bar.close > ma3:
            strength = min(1.0, pct_change * 4 + (volume_ratio - 1) * 0.4)
            return Signal(
                SignalType.BUY, bar.timestamp, bar.close, strength,
                f"龙头(优化): 涨幅{pct_change*100:.1f}%, RSI{rsi:.0f}, 量比{volume_ratio:.1f}x"
            )
        
        return Signal(SignalType.HOLD, bar.timestamp, bar.close, reason="未达条件")


def run_optimized_backtest():
    """运行优化版回测"""
    
    print("=" * 60)
    print("🚀 200%年收益策略 - 优化版回测")
    print("=" * 60)
    
    # 查找所有180天数据
    cache_dir = '/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang/data/cache'
    data_files = [f for f in os.listdir(cache_dir) if f.endswith('.csv') and '180d' in f]
    
    if not data_files:
        print("❌ 没有找到180天的数据文件")
        return
    
    config = OptimizedConfig()
    
    all_results = {}
    
    # 测试每个数据文件
    for data_file in data_files[:5]:  # 只测试前5个
        file_path = os.path.join(cache_dir, data_file)
        symbol = data_file.split('_')[0]
        
        print(f"\n{'='*60}")
        print(f"📊 测试股票: {symbol}")
        print(f"{'='*60}")
        
        # 加载数据
        df = pd.read_csv(file_path)
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
        
        print(f"✓ 加载 {len(bars)} 条K线")
        
        # 测试优化版策略
        strategies = [
            ("火箭(优化)", OptimizedRocket(config)),
            ("龙头(优化)", OptimizedDragon(config))
        ]
        
        for name, strategy in strategies:
            # 重置策略
            strategy._bars = []
            
            # 回测
            cash = 1000000
            position = None
            trades = []
            
            for bar in bars:
                strategy.update(bar)
                
                # 持仓检查
                if position and position['quantity'] > 0:
                    current_price = bar.close
                    pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                    
                    if current_price > position['highest']:
                        position['highest'] = current_price
                    
                    # 止损
                    if pnl_pct <= config.stop_loss:
                        cash += position['quantity'] * current_price
                        trades.append({'pnl_pct': pnl_pct})
                        position = None
                    
                    # 第一止盈
                    elif pnl_pct >= config.take_profit_1 and not position.get('tp1'):
                        sell_qty = position['quantity'] * 0.5
                        cash += sell_qty * current_price
                        position['quantity'] -= sell_qty
                        position['tp1'] = True
                        trades.append({'pnl_pct': pnl_pct})
                    
                    # 第二止盈
                    elif pnl_pct >= config.take_profit_2:
                        cash += position['quantity'] * current_price
                        trades.append({'pnl_pct': pnl_pct})
                        position = None
                    
                    # 移动止损
                    elif current_price <= position['highest'] * (1 - config.trailing_stop):
                        cash += position['quantity'] * current_price
                        trades.append({'pnl_pct': pnl_pct})
                        position = None
                
                # 买入
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
                            'tp1': False
                        }
            
            # 最终价值
            final_value = cash
            if position:
                final_value += position['quantity'] * bars[-1].close
            
            # 统计
            total_return = (final_value - 1000000) / 1000000
            annual_return = total_return * (252 / len(bars))
            win_rate = len([t for t in trades if t['pnl_pct'] > 0]) / len(trades) if trades else 0
            
            print(f"{name}:")
            print(f"  年化收益: {annual_return*100:.2f}%")
            print(f"  总收益: {total_return*100:.2f}%")
            print(f"  交易: {len(trades)}次")
            print(f"  胜率: {win_rate*100:.1f}%")
            
            key = f"{symbol}_{name}"
            all_results[key] = {
                'symbol': symbol,
                'strategy': name,
                'annual_return': annual_return,
                'total_return': total_return,
                'trades': len(trades),
                'win_rate': win_rate
            }
    
    # 最佳组合
    best = max(all_results.items(), key=lambda x: x[1]['annual_return'])
    
    print("\n" + "=" * 60)
    print("🏆 最佳组合")
    print("=" * 60)
    print(f"股票: {best[1]['symbol']}")
    print(f"策略: {best[1]['strategy']}")
    print(f"年化收益: {best[1]['annual_return']*100:.2f}%")
    print(f"总收益: {best[1]['total_return']*100:.2f}%")
    
    return all_results


if __name__ == "__main__":
    run_optimized_backtest()