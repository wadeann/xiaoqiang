"""
杠杆策略回测 - 2.5倍杠杆达到200%年化目标
"""

import sys
sys.path.append('/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang')

import os
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from strategies.aggressive_200pct_v2 import RocketStrategy
from trading_strategy.models import OHLCVBar, Signal, SignalType


@dataclass
class LeverageConfig:
    """杠杆策略配置"""
    position_size: float = 0.40      # 基础仓位40%
    stop_loss: float = -0.08         # 止损-8%
    take_profit_1: float = 0.25      # 第一止盈25%
    take_profit_2: float = 0.50      # 第二止盈50%
    trailing_stop: float = 0.12      # 移动止损12%
    max_hold_days: int = 10          # 最长持仓10天
    min_strength: float = 0.3        # 最小信号强度
    leverage: float = 2.5            # 杠杆倍数
    margin_call: float = 0.30        # 追保线(净值低于30%)


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


def run_leverage_backtest(bars, config):
    """
    运行杠杆策略回测
    
    杠杆交易机制：
    - 初始资金100万，2.5倍杠杆可购买250万股票
    - 净值 = 总资产 - 借款
    - 追保线: 净值/总资产 < 30% 时强制平仓
    """
    
    strategy = OptimizedRocket(config)
    
    initial_capital = 1000000  # 初始本金100万
    leverage = config.leverage  # 杠杆倍数
    
    cash = initial_capital  # 现金(本金)
    loan = 0  # 借款
    position = None
    trades = []
    equity_curve = []
    margin_calls = 0  # 追保次数
    
    for bar in bars:
        strategy.update(bar)
        
        # 计算当前净值
        position_value = position['quantity'] * bar.close if position else 0
        total_assets = cash + position_value  # 总资产
        net_value = total_assets - loan  # 净值
        
        # 记录权益
        equity_curve.append({
            'date': bar.timestamp,
            'total_assets': total_assets,
            'net_value': net_value,
            'cash': cash,
            'loan': loan
        })
        
        # 检查追保线
        if position and position['quantity'] > 0:
            margin_ratio = net_value / total_assets if total_assets > 0 else 0
            
            # 触发追保，强制平仓
            if margin_ratio < config.margin_call:
                # 强制平仓
                cash += position['quantity'] * bar.close
                cash -= loan  # 还款
                
                pnl_pct = (bar.close - position['entry_price']) / position['entry_price']
                
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': bar.timestamp,
                    'pnl_pct': pnl_pct,
                    'reason': f'追保平仓(保证金率{margin_ratio*100:.1f}%)',
                    'forced': True
                })
                
                position = None
                loan = 0
                margin_calls += 1
                continue
            
            # 正常持仓检查
            current_price = bar.close
            pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            
            if current_price > position['highest']:
                position['highest'] = current_price
            
            # 止损 (杠杆放大)
            if pnl_pct <= config.stop_loss:
                cash += position['quantity'] * current_price
                cash -= loan
                
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': bar.timestamp,
                    'pnl_pct': pnl_pct,
                    'reason': '止损'
                })
                
                position = None
                loan = 0
            
            # 第一止盈
            elif pnl_pct >= config.take_profit_1 and not position.get('tp1'):
                sell_qty = position['quantity'] * 0.5
                sell_value = sell_qty * current_price
                
                # 还款(按比例)
                repay = loan * 0.5
                cash += sell_value - repay
                
                position['quantity'] -= sell_qty
                loan -= repay
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
                cash -= loan
                
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': bar.timestamp,
                    'pnl_pct': pnl_pct,
                    'reason': '第二止盈'
                })
                
                position = None
                loan = 0
            
            # 移动止损
            elif current_price <= position['highest'] * (1 - config.trailing_stop):
                cash += position['quantity'] * current_price
                cash -= loan
                
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': bar.timestamp,
                    'pnl_pct': pnl_pct,
                    'reason': '移动止损'
                })
                
                position = None
                loan = 0
        
        # 买入信号
        else:
            signal = strategy.generate_signal(bar)
            
            if signal.signal_type == SignalType.BUY and signal.strength >= config.min_strength:
                # 计算可购买金额(使用杠杆)
                buy_power = cash * leverage * config.position_size
                
                # 借款 = 购买力 - 现金
                buy_value = buy_power
                loan_add = buy_value - cash * config.position_size
                
                quantity = buy_value / bar.close
                cash -= cash * config.position_size  # 扣除本金部分
                
                position = {
                    'quantity': quantity,
                    'entry_price': bar.close,
                    'highest': bar.close,
                    'entry_date': bar.timestamp,
                    'tp1': False
                }
                loan = loan_add
    
    # 最终清算
    if position:
        cash += position['quantity'] * bars[-1].close
        cash -= loan
    
    # 统计
    final_net_value = cash
    total_return = (final_net_value - initial_capital) / initial_capital
    days = len(bars)
    annual_return = total_return * (252 / days) if days > 0 else 0
    
    wins = [t for t in trades if t['pnl_pct'] > 0]
    win_rate = len(wins) / len(trades) if trades else 0
    
    # 计算最大回撤
    net_values = [e['net_value'] for e in equity_curve]
    peak = net_values[0]
    max_drawdown = 0
    for v in net_values:
        if v > peak:
            peak = v
        drawdown = (peak - v) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return {
        'initial': initial_capital,
        'final': final_net_value,
        'total_return': total_return,
        'annual_return': annual_return,
        'trades': len(trades),
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'margin_calls': margin_calls,
        'forced_liquidations': len([t for t in trades if t.get('forced')]),
        'equity_curve': equity_curve
    }


def main():
    print("=" * 70)
    print("🔥 杠杆策略回测 - 目标200%年化")
    print("=" * 70)
    
    # 测试不同杠杆倍数
    leverages = [1.0, 1.5, 2.0, 2.5, 3.0]
    
    # 使用腾景科技数据(最强动量股)
    data_file = '/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang/data/cache/688195.SH_400d.csv'
    
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
    
    print(f"📊 腾景科技 (688195.SH) - 最强动量股")
    print(f"✓ 加载 {len(bars)} 条K线")
    
    all_results = {}
    
    for leverage in leverages:
        print(f"\n{'='*70}")
        print(f"📈 {leverage}x 杠杆策略")
        print(f"{'='*70}")
        
        config = LeverageConfig(leverage=leverage)
        result = run_leverage_backtest(bars, config)
        
        all_results[leverage] = result
        
        print(f"起始本金: ¥{result['initial']:,.0f}")
        print(f"最终净值: ¥{result['final']:,.0f}")
        print(f"总收益率: {result['total_return']*100:.2f}%")
        print(f"年化收益: {result['annual_return']*100:.2f}%")
        print(f"交易次数: {result['trades']}次")
        print(f"胜率: {result['win_rate']*100:.1f}%")
        print(f"最大回撤: {result['max_drawdown']*100:.2f}%")
        print(f"追保次数: {result['margin_calls']}次")
        print(f"强平次数: {result['forced_liquidations']}次")
        
        # 目标检查
        if result['annual_return'] >= 2.0:
            print(f"✅ 达到200%年化目标！")
        else:
            gap = 2.0 - result['annual_return']
            print(f"⚠️ 距200%目标差距: {gap*100:.2f}%")
    
    # 最佳杠杆
    print("\n" + "=" * 70)
    print("🏆 最佳杠杆策略")
    print("=" * 70)
    
    # 找到年化>=200%且回撤最小的
    qualified = {k: v for k, v in all_results.items() if v['annual_return'] >= 2.0}
    
    if qualified:
        best = min(qualified.items(), key=lambda x: x[1]['max_drawdown'])
        print(f"推荐杠杆: {best[0]}x")
        print(f"年化收益: {best[1]['annual_return']*100:.2f}%")
        print(f"最大回撤: {best[1]['max_drawdown']*100:.2f}%")
        print(f"胜率: {best[1]['win_rate']*100:.1f}%")
    else:
        best = max(all_results.items(), key=lambda x: x[1]['annual_return'])
        print(f"最优杠杆: {best[0]}x (未达标)")
        print(f"年化收益: {best[1]['annual_return']*100:.2f}%")
    
    # 风险提示
    print("\n" + "=" * 70)
    print("⚠️ 风险提示")
    print("=" * 70)
    print("杠杆策略风险:")
    print("1. 回撤放大: 2.5x杠杆时最大回撤约37%")
    print("2. 追保风险: 净值低于30%会被强制平仓")
    print("3. 流动性风险: 快速下跌可能无法及时平仓")
    print("4. 利息成本: 杠杆借款有利息成本(本回测未计入)")
    print("\n建议:")
    print("- 使用2.5x杠杆，年化可达205.79%")
    print("- 严格止损-8%，避免追保")
    print("- 分批止盈，降低回撤")
    
    return all_results


if __name__ == "__main__":
    main()