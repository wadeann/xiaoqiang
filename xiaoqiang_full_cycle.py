#!/usr/bin/env python3
"""
华尔街之狼 - 完整周期
扫描 → 交易 → 复盘 → 进化
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 导入模块
sys.path.insert(0, '.')

def run_full_cycle():
    """运行完整周期"""
    print("\n" + "=" * 70)
    print("🐺 华尔街之狼 - 完整周期")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 1. 每日复盘
    print("\n📊 步骤 1: 每日复盘")
    print("-" * 70)
    from daily_report import DailyReporter
    reporter = DailyReporter()
    reporter.generate_report()
    
    # 2. 自我进化
    print("\n🧬 步骤 2: 自我进化")
    print("-" * 70)
    from evolution import evolve
    evolve()
    
    # 3. 更新观察列表
    print("\n📋 步骤 3: 更新观察列表")
    print("-" * 70)
    from daily_review import scan_and_add, check_rules
    added = scan_and_add()
    if added:
        print(f"新增标的: {len(added)} 只")
        for symbol, change in added:
            print(f"  ✅ {symbol}: +{change:.2f}%")
    else:
        print("无新增标的")
    
    removed = check_rules()
    if removed:
        print(f"剔除标的: {len(removed)} 只")
        for symbol, reason in removed:
            print(f"  ❌ {symbol}: {reason}")
    else:
        print("无需剔除")
    
    # 4. 扫描交易机会
    print("\n🔍 步骤 4: 扫描交易机会")
    print("-" * 70)
    from xiaoqiang_trader import WolfTrader
    wolf = WolfTrader()
    opportunities = wolf.scan_market()
    
    # 5. 执行交易 (交易时段)
    print("\n💹 步骤 5: 执行交易")
    print("-" * 70)
    hour = datetime.now().hour
    is_trading = (hour >= 21 or hour < 4) or (hour >= 9 and hour < 16)
    
    if is_trading:
        print("交易时段，执行交易...")
        wolf.run()
    else:
        print("非交易时段，仅扫描不交易")
    
    # 6. 生成最终报告
    print("\n" + "=" * 70)
    print("✅ 完整周期执行完成")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="华尔街之狼完整周期")
    parser.add_argument("--cycle", action="store_true", help="运行完整周期")
    parser.add_argument("--report", action="store_true", help="仅生成报告")
    parser.add_argument("--evolve", action="store_true", help="仅自我进化")
    
    args = parser.parse_args()
    
    if args.cycle:
        run_full_cycle()
    elif args.report:
        from daily_report import DailyReporter
        DailyReporter().generate_report()
    elif args.evolve:
        from evolution import evolve
        evolve()
    else:
        run_full_cycle()
