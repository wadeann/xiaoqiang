#!/usr/bin/env python3
"""
小强量化系统 - 回测入口
支持: 模拟回测、参数优化
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from backtest.run_backtest import BacktestEngine
from strategies.momentum import MomentumStrategy, MomentumStrategyV2


def generate_mock_data(symbols: list, days: int = 60, seed: int = 42) -> dict:
    """生成模拟历史数据"""
    np.random.seed(seed)
    
    data = {}
    base_prices = {
        "300308.SZ": 550,   # 中际旭创
        "300394.SZ": 300,   # 天孚通信
        "300502.SZ": 420,   # 新易盛
        "002281.SZ": 80,    # 光迅科技
        "688205.SH": 200,   # 德科立
        "688195.SH": 280,   # 腾景科技
        "688307.SH": 70,    # 中润光学
        "NVDA": 170,        # 英伟达
        "TSLA": 370,        # 特斯拉
        "ARM": 140,         # ARM
    }
    
    for symbol in symbols:
        base_price = base_prices.get(symbol, 100)
        
        # 模拟价格走势
        dates = pd.date_range(end=datetime.now(), periods=days, freq="B")
        
        # 随机游走 + 趋势
        returns = np.random.randn(days) * 0.03 + 0.001  # 日波动 3%，平均收益 0.1%
        prices = base_price * np.cumprod(1 + returns)
        
        # 生成 OHLCV
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "open": prices * (1 + np.random.randn(days) * 0.01),
            "close": prices,
            "high": prices * (1 + np.abs(np.random.randn(days) * 0.015)),
            "low": prices * (1 - np.abs(np.random.randn(days) * 0.015)),
            "volume": np.random.randint(1000000, 10000000, days),
            "change_pct": returns * 100,
            "symbol": symbol
        })
        
        data[symbol] = df
    
    return data


def run_backtest_test():
    """运行回测测试"""
    print("=" * 60)
    print("🧪 小强量化系统 - 回测测试")
    print("=" * 60)
    
    # 测试标的
    symbols = ["300308.SZ", "300394.SZ", "300502.SZ", "002281.SZ", "688205.SH"]
    
    # 生成模拟数据
    print("\n📥 生成模拟历史数据...")
    data = generate_mock_data(symbols, days=60)
    for symbol, df in data.items():
        print(f"  {symbol}: {len(df)} 条记录, 价格范围 {df['close'].min():.2f} ~ {df['close'].max():.2f}")
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    # 测试不同参数
    print("\n" + "=" * 60)
    print("📊 策略参数优化测试")
    print("=" * 60)
    
    results_list = []
    
    for min_change in [2.0, 3.0, 5.0]:
        for top_n in [2, 3, 5]:
            strategy = MomentumStrategy(top_n=top_n, min_change_pct=min_change)
            
            results = engine.run_backtest(
                data, strategy,
                commission=0.001,
                slippage=0.001,
                position_size=0.2,
                max_positions=5
            )
            
            if "error" not in results:
                results_list.append({
                    "min_change": min_change,
                    "top_n": top_n,
                    "pnl_rate": results["pnl_rate"],
                    "max_drawdown": results["max_drawdown"],
                    "sharpe": results["sharpe_ratio"],
                    "win_rate": results["win_rate"],
                    "trades": results["total_trades"]
                })
    
    # 排序
    results_list.sort(key=lambda x: x["pnl_rate"], reverse=True)
    
    print("\n📈 参数优化结果:")
    print(f"{'涨幅阈值':<10} {'买入数量':<10} {'收益率':<12} {'最大回撤':<12} {'夏普':<10} {'胜率':<10} {'交易次数':<10}")
    print("-" * 74)
    for r in results_list[:10]:
        print(f"{r['min_change']:<10.1f} {r['top_n']:<10} {r['pnl_rate']*100:>10.2f}% {r['max_drawdown']*100:>10.2f}% {r['sharpe']:>10.2f} {r['win_rate']*100:>8.2f}% {r['trades']:>10}")
    
    # 最优参数回测详细结果
    if results_list:
        best = results_list[0]
        print(f"\n✅ 最优参数: 涨幅阈值 {best['min_change']}%, 买入数量 {best['top_n']}")
        print(f"   收益率: {best['pnl_rate']*100:.2f}%")
        print(f"   最大回撤: {best['max_drawdown']*100:.2f}%")
        print(f"   夏普比率: {best['sharpe']:.2f}")
        print(f"   胜率: {best['win_rate']*100:.2f}%")
    
    return results_list


def run_real_backtest(symbols: list = None, days: int = 60):
    """运行真实数据回测"""
    if symbols is None:
        symbols = ["300308.SZ", "300394.SZ", "300502.SZ", "002281.SZ", "688205.SH"]
    
    print("=" * 60)
    print("📊 小强量化系统 - 真实数据回测")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    # 尝试加载真实数据
    print("\n📥 加载历史数据...")
    data = {}
    for symbol in symbols:
        df = engine.data_loader.load_a_share_history(symbol, days=days)
        if not df.empty:
            data[symbol] = df
            print(f"  ✅ {symbol}: {len(df)} 条记录")
        else:
            print(f"  ❌ {symbol}: 加载失败")
    
    if not data:
        print("\n⚠️ 无法加载真实数据，使用模拟数据")
        data = generate_mock_data(symbols, days)
    
    # 运行回测
    strategy = MomentumStrategy(top_n=3, min_change_pct=3.0)
    results = engine.run_backtest(data, strategy)
    
    # 打印结果
    engine.print_results(results)
    
    # 保存结果
    engine.save_results(results)
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="小强量化系统 - 回测")
    parser.add_argument("--mock", action="store_true", help="使用模拟数据")
    parser.add_argument("--days", type=int, default=60, help="回测天数")
    parser.add_argument("--symbols", nargs="+", help="回测标的")
    
    args = parser.parse_args()
    
    if args.mock:
        run_backtest_test()
    else:
        symbols = args.symbols if args.symbols else None
        run_real_backtest(symbols=symbols, days=args.days)
