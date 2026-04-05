"""
200%年收益策略回测验证

使用小强量化系统的历史数据进行回测验证
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# 导入策略模块
from strategies.aggressive_200pct import (
    DragonCatcher, 
    MomentumRocket, 
    SectorRotation,
    Aggressive200Config,
    STRATEGY_SETS
)
from models import OHLCVBar, Signal, SignalType, Portfolio, Trade
from utils.data_generator import generate_sample_bars


class AggressiveBacktest:
    """激进策略回测引擎"""
    
    def __init__(self, strategy, config: Aggressive200Config):
        self.strategy = strategy
        self.config = config
        self.results = []
        
    def run(self, bars: List[OHLCVBar], initial_capital: float = 1000000) -> Dict:
        """
        运行回测
        
        Args:
            bars: K线数据
            initial_capital: 初始资金
            
        Returns:
            回测结果字典
        """
        portfolio = Portfolio(
            initial_capital=initial_capital,
            cash=initial_capital
        )
        
        trades = []
        position = None  # 当前持仓
        highest_price = 0  # 最高价跟踪
        entry_date = None
        
        for i, bar in enumerate(bars):
            # 更新策略数据
            self.strategy.update(bar)
            
            # 如果有持仓，检查止损止盈
            if position and position['quantity'] > 0:
                current_price = bar.close
                
                # 更新最高价
                if current_price > highest_price:
                    highest_price = current_price
                
                # 计算盈亏
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                
                # 移动止损检查
                trailing_stop_price = highest_price * (1 - self.config.trailing_stop)
                
                # 止损
                if pnl_pct <= self.config.stop_loss:
                    # 卖出
                    sell_value = position['quantity'] * current_price
                    portfolio.cash += sell_value
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': bar.timestamp,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_reason': '止损'
                    })
                    
                    position = None
                    highest_price = 0
                    entry_date = None
                    
                # 第一止盈点 (卖出50%)
                elif pnl_pct >= self.config.take_profit_1 and position.get('tp1_hit', False) == False:
                    sell_quantity = position['quantity'] * 0.5
                    sell_value = sell_quantity * current_price
                    portfolio.cash += sell_value
                    
                    position['quantity'] -= sell_quantity
                    position['tp1_hit'] = True
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': bar.timestamp,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'quantity': sell_quantity,
                        'pnl': (current_price - position['entry_price']) * sell_quantity,
                        'pnl_pct': pnl_pct,
                        'exit_reason': '第一止盈'
                    })
                
                # 第二止盈点 (清仓)
                elif pnl_pct >= self.config.take_profit_2:
                    sell_value = position['quantity'] * current_price
                    portfolio.cash += sell_value
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': bar.timestamp,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': (current_price - position['entry_price']) * position['quantity'],
                        'pnl_pct': pnl_pct,
                        'exit_reason': '第二止盈'
                    })
                    
                    position = None
                    highest_price = 0
                    entry_date = None
                
                # 移动止损
                elif current_price <= trailing_stop_price and pnl_pct > 0:
                    sell_value = position['quantity'] * current_price
                    portfolio.cash += sell_value
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': bar.timestamp,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': (current_price - position['entry_price']) * position['quantity'],
                        'pnl_pct': pnl_pct,
                        'exit_reason': '移动止损'
                    })
                    
                    position = None
                    highest_price = 0
                    entry_date = None
                
                # 最长持仓天数检查
                elif entry_date and (bar.timestamp - entry_date).days >= self.config.max_hold_days:
                    sell_value = position['quantity'] * current_price
                    portfolio.cash += sell_value
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': bar.timestamp,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'quantity': position['quantity'],
                        'pnl': (current_price - position['entry_price']) * position['quantity'],
                        'pnl_pct': pnl_pct,
                        'exit_reason': '时间止损'
                    })
                    
                    position = None
                    highest_price = 0
                    entry_date = None
            
            # 如果没有持仓，检查买入信号
            else:
                signal = self.strategy.generate_signal(bar)
                
                if signal.signal_type == SignalType.BUY and signal.strength >= self.config.min_strength:
                    # 买入
                    buy_value = portfolio.cash * self.config.position_size
                    quantity = buy_value / bar.close
                    
                    position = {
                        'entry_price': bar.close,
                        'quantity': quantity,
                        'tp1_hit': False
                    }
                    highest_price = bar.close
                    entry_date = bar.timestamp
                    
                    portfolio.cash -= buy_value
            
            # 更新权益
            if position:
                portfolio.position_value = position['quantity'] * bar.close
            else:
                portfolio.position_value = 0
            
            portfolio.total_value = portfolio.cash + portfolio.position_value
        
        # 计算绩效
        total_return = (portfolio.total_value - initial_capital) / initial_capital
        
        if trades:
            wins = [t for t in trades if t['pnl'] > 0]
            win_rate = len(wins) / len(trades) if trades else 0
            avg_pnl = np.mean([t['pnl_pct'] for t in trades]) if trades else 0
        else:
            win_rate = 0
            avg_pnl = 0
        
        # 年化收益率 (假设回测周期为120天)
        days = len(bars)
        annual_return = total_return * (252 / days) if days > 0 else 0
        
        return {
            'initial_capital': initial_capital,
            'final_value': portfolio.total_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_pnl_pct': avg_pnl,
            'trades': trades
        }


def run_backtest_comparison():
    """运行策略对比回测"""
    
    print("=" * 60)
    print("🎯 200%年收益策略回测验证")
    print("=" * 60)
    
    # 生成测试数据 (模拟180天数据)
    print("\n📊 生成测试数据...")
    bars = generate_sample_bars(
        start_date=datetime(2025, 10, 1),
        num_bars=180,
        initial_price=100.0,
        volatility=0.03,  # 更高的波动率
        trend=0.002,      # 更强的趋势
        seed=42
    )
    print(f"✓ 生成 {len(bars)} 天K线数据")
    
    results = {}
    
    # 测试每套策略
    for strategy_key, strategy_config in STRATEGY_SETS.items():
        print(f"\n{'='*60}")
        print(f"📈 策略: {strategy_config['name']}")
        print(f"{'='*60}")
        
        strategy_class = strategy_config['strategies'][0]  # 取第一个策略
        config = strategy_config['config']
        
        # 创建策略实例
        strategy = strategy_class(config)
        
        # 运行回测
        backtest = AggressiveBacktest(strategy, config)
        result = backtest.run(bars)
        
        results[strategy_key] = result
        
        # 打印结果
        print(f"起始资金: ¥{result['initial_capital']:,.0f}")
        print(f"最终权益: ¥{result['final_value']:,.0f}")
        print(f"总收益率: {result['total_return']*100:.2f}%")
        print(f"年化收益: {result['annual_return']*100:.2f}%")
        print(f"交易次数: {result['total_trades']}")
        print(f"胜率: {result['win_rate']*100:.2f}%")
        print(f"平均盈亏: {result['avg_pnl_pct']*100:.2f}%")
        
        # 目标检查
        target = strategy_config['target_return']
        if result['annual_return'] >= target:
            print(f"✅ 达到目标 ({target*100:.0f}%年化)")
        else:
            gap = target - result['annual_return']
            print(f"⚠️ 未达目标，差距: {gap*100:.2f}%")
    
    # 最佳策略
    best_strategy = max(results.items(), key=lambda x: x[1]['annual_return'])
    
    print("\n" + "=" * 60)
    print("🏆 最佳策略")
    print("=" * 60)
    print(f"策略: {STRATEGY_SETS[best_strategy[0]]['name']}")
    print(f"年化收益: {best_strategy[1]['annual_return']*100:.2f}%")
    print(f"总收益: {best_strategy[1]['total_return']*100:.2f}%")
    
    return results


if __name__ == "__main__":
    results = run_backtest_comparison()