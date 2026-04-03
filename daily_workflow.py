#!/usr/bin/env python3
"""
小强每日工作流
- 早间：A股盘前分析
- 晚间：抓龙行动
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from strategies.momentum import MomentumStrategy
from strategies.trend_following import TrendFollowingStrategy
from data.rockflow_adapter import RockflowAdapter
from executor.trader import Trader
import json


def morning_analysis():
    """早间 A股盘前分析"""
    print("=" * 60)
    print("🌅 小强早间分析 - A股盘前策略")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 美股大盘情况
    print("📊 美股大盘扫描...")
    adapter = RockflowAdapter()
    
    # 美股主要指数 (用代表性标的)
    us_tickers = ['NVDA', 'TSLA', 'MU', 'ARM', 'ASML', 'TSM']
    us_quotes = adapter.get_quotes(us_tickers)
    
    if us_quotes:
        print("\n🇺🇸 美股 AI/半导体板块:")
        total_change = 0
        for quote in us_quotes:
            symbol = quote.get('symbol', 'N/A')
            change_pct = quote.get('change_pct', 0)
            total_change += change_pct
            emoji = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
            print(f"  {emoji} {symbol}: {change_pct:+.2f}%")
        
        avg_change = total_change / len(us_quotes) if us_quotes else 0
        print(f"\n📈 板块平均涨跌: {avg_change:+.2f}%")
    
    # 2. A股相关标的
    print("\n📊 A股相关标的...")
    cn_quotes = adapter.get_quotes(['00700.HK', '09988.HK', '00981.HK'])
    
    if cn_quotes:
        print("\n🇨🇳 港股科技:")
        for quote in cn_quotes:
            symbol = quote.get('symbol', 'N/A')
            change_pct = quote.get('change_pct', 0)
            emoji = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
            print(f"  {emoji} {symbol}: {change_pct:+.2f}%")
    
    # 3. A股盘前策略建议
    print("\n" + "=" * 60)
    print("📋 A股盘前策略建议")
    print("=" * 60)
    
    if us_quotes:
        avg_us = sum(q.get('change_pct', 0) for q in us_quotes) / len(us_quotes)
        
        if avg_us > 2:
            print("🔥 美股AI板块大涨 → A股科技股高开概率大")
            print("   建议: 关注半导体、AI算力板块")
            print("   策略: 开盘逢低买入")
        elif avg_us > 0:
            print("✅ 美股AI板块上涨 → A股科技股偏乐观")
            print("   建议: 持有为主，适度加仓")
        elif avg_us > -2:
            print("⚠️ 美股AI板块微跌 → A股科技股观望")
            print("   建议: 等待企稳信号")
        else:
            print("🔴 美股AI板块大跌 → A股科技股承压")
            print("   建议: 降低仓位，规避风险")
    
    print("\n" + "=" * 60)
    print("✅ 早间分析完成")
    print("=" * 60)


def evening_catch_dragon():
    """晚间抓龙行动"""
    print("=" * 60)
    print("🐉 小强晚间行动 - 抓龙")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 导入主程序逻辑
    from main import main
    
    # 执行扫描模式
    print("📊 扫描市场...")
    import argparse
    args = argparse.Namespace(mode='scan', target=1.0, stop_loss=-0.1)
    main()


def daily_report():
    """每日收盘汇报"""
    print("=" * 60)
    print("📊 小强每日汇报")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    from main import main
    import argparse
    args = argparse.Namespace(mode='scan', target=1.0, stop_loss=-0.1)
    main()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='小强每日工作流')
    parser.add_argument('--mode', type=str, default='morning',
                        choices=['morning', 'evening', 'report'],
                        help='运行模式: morning=早间分析, evening=晚间抓龙, report=每日汇报')
    
    args = parser.parse_args()
    
    if args.mode == 'morning':
        morning_analysis()
    elif args.mode == 'evening':
        evening_catch_dragon()
    elif args.mode == 'report':
        daily_report()
