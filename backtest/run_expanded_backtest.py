#!/usr/bin/env python3
"""
小强量化系统 - 扩展股票池回测
获取热门板块股票进行大规模回测
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
from backtest.qlib_backtest import EnhancedBacktest, MultiFactorAnalyzer


# 热门板块股票池 (扩展到100只)
HOT_STOCKS = {
    # ===== AI/算力板块 =====
    "AI芯片": [
        "300474.SZ",  # 景嘉微
        "688981.SH",  # 中芯国际
        "002049.SZ",  # 紫光国微
        "688256.SH",  # 寒武纪
        "688041.SH",  # 海光信息
        "688045.SH",  # 必易微
        "688396.SH",  # 华润微
        "688521.SH",  # 芯原股份
    ],
    
    "光模块/光通信": [
        "300308.SZ",  # 中际旭创
        "300394.SZ",  # 天孚通信
        "300502.SZ",  # 新易盛
        "002281.SZ",  # 光迅科技
        "300570.SZ",  # 太辰光
        "688205.SH",  # 德科立
        "688195.SH",  # 腾景科技
        "688307.SH",  # 中润光学
        "603118.SH",  # 共进股份
        "002792.SZ",  # 通宇通讯
    ],
    
    "AI算力/服务器": [
        "000977.SZ",  # 浪潮信息
        "002230.SZ",  # 科大讯飞
        "300033.SZ",  # 同花顺
        "000063.SZ",  # 中兴通讯
        "002415.SZ",  # 海康威视
        "300454.SZ",  # 深信服
        "688111.SH",  # 金山办公
        "688787.SH",  # 海天瑞声
    ],
    
    # ===== 半导体板块 =====
    "半导体设备": [
        "603501.SH",  # 韦尔股份
        "002371.SZ",  # 北方华创
        "300661.SZ",  # 圣邦股份
        "688012.SH",  # 中微公司
        "688120.SH",  # 华峰测控
        "688037.SH",  # 芯源微
        "688147.SH",  # 盛美上海
        "002156.SZ",  # 通富微电
        "688008.SH",  # 澜起科技
        "688599.SH",  # 天合光能
    ],
    
    "半导体材料": [
        "688126.SH",  # 沪硅产业
        "688083.SH",  # 中望软件
        "300236.SZ",  # 上海新阳
        "002407.SZ",  # 多氟多
        "603160.SH",  # 汇顶科技
    ],
    
    # ===== 新能源板块 =====
    "锂电池": [
        "300750.SZ",  # 宁德时代
        "002594.SZ",  # 比亚迪
        "002812.SZ",  # 恩捷股份
        "300014.SZ",  # 亿纬锂能
        "002466.SZ",  # 天齐锂业
        "002460.SZ",  # 赣锋锂业
        "300769.SZ",  # 德方纳米
        "688005.SH",  # 容百科技
    ],
    
    "光伏": [
        "601012.SH",  # 隆基绿能
        "600438.SH",  # 通威股份
        "002459.SZ",  # 晶澳科技
        "688599.SH",  # 天合光能
        "605117.SH",  # 德业股份
        "688303.SH",  # 大全能源
    ],
    
    "储能": [
        "300763.SZ",  # 锦浪科技
        "688390.SH",  # 固德威
        "688063.SH",  # 德业股份
        "300274.SZ",  # 阳光电源
    ],
    
    # ===== 消费电子 =====
    "消费电子": [
        "000725.SZ",  # 京东方A
        "002475.SZ",  # 立讯精密
        "000063.SZ",  # 中兴通讯
        "002241.SZ",  # 歌尔股份
        "603501.SH",  # 韦尔股份
        "002600.SZ",  # 领益智造
        "603160.SH",  # 汇顶科技
    ],
    
    # ===== 医药生物 =====
    "创新药": [
        "300760.SZ",  # 迈瑞医疗
        "688180.SH",  # 君实生物
        "688235.SH",  # 百济神州
        "300122.SZ",  # 智飞生物
        "300347.SZ",  # 泰格医药
        "688111.SH",  # 金山办公
    ],
    
    "医疗器械": [
        "300760.SZ",  # 迈瑞医疗
        "688050.SH",  # 爱博医疗
        "688108.SH",  # 赛诺医疗
        "300015.SZ",  # 爱尔眼科
    ],
    
    # ===== 金融科技 =====
    "金融科技": [
        "300033.SZ",  # 同花顺
        "300368.SZ",  # 汇金股份
        "002405.SZ",  # 四维图新
        "600570.SH",  # 恒生电子
        "300468.SZ",  # 四方精创
    ],
    
    # ===== 机器人 =====
    "机器人": [
        "300024.SZ",  # 机器人
        "002747.SZ",  # 埃斯顿
        "688169.SH",  # 石头科技
        "300124.SZ",  # 汇川技术
        "002633.SZ",  # 申科智能
    ],
    
    # ===== 汽车零部件 =====
    "汽车零部件": [
        "002594.SZ",  # 比亚迪
        "002920.SZ",  # 德赛西威
        "603906.SH",  # 龙蟠科技
        "002407.SZ",  # 多氟多
        "300457.SZ",  # 赢合科技
    ],
}


def get_sector_stocks():
    """获取所有板块股票列表"""
    all_stocks = []
    for sector, stocks in HOT_STOCKS.items():
        all_stocks.extend(stocks)
    return list(set(all_stocks))  # 去重


def run_expanded_backtest(days: int = 90, top_n: int = 5, min_score: float = 0.15):
    """运行扩展回测"""
    print("=" * 70)
    print("🐉 小强量化系统 - 扩展股票池回测")
    print("=" * 70)
    
    # 获取所有股票
    all_stocks = get_sector_stocks()
    print(f"📊 股票池: {len(all_stocks)} 只")
    print(f"📅 回测周期: {days} 天")
    print(f"🎯 选股策略: Top {top_n}, 最低得分 {min_score}")
    
    # 按板块显示
    print("\n📋 板块分布:")
    for sector, stocks in HOT_STOCKS.items():
        print(f"  {sector}: {len(stocks)} 只")
    
    # 创建回测引擎
    engine = EnhancedBacktest()
    
    # 加载数据
    print(f"\n📥 加载历史数据...")
    data = engine.load_data(all_stocks, days=days)
    
    if not data:
        print("❌ 没有加载数据")
        return None
    
    # 运行回测
    print(f"\n🔄 运行多因子策略回测...")
    results = engine.run_backtest(
        data,
        strategy="multi_factor",
        position_size=0.15,
        max_positions=8,
        top_n=top_n,
        min_score=min_score
    )
    
    # 打印结果
    engine.print_results(results)
    
    # 生成报告
    engine.generate_report(results)
    
    # 分析各板块表现
    print("\n" + "=" * 70)
    print("📊 各板块表现分析")
    print("=" * 70)
    
    trades_df = pd.DataFrame(results['trades'])
    sell_trades = trades_df[trades_df['type'] == 'SELL']
    
    sector_performance = {}
    for sector, stocks in HOT_STOCKS.items():
        sector_trades = sell_trades[sell_trades['symbol'].isin(stocks)]
        if not sector_trades.empty:
            total_pnl = sector_trades['pnl'].sum()
            win_rate = (sector_trades['pnl'] > 0).sum() / len(sector_trades)
            avg_pnl = sector_trades['pnl'].mean()
            sector_performance[sector] = {
                'trades': len(sector_trades),
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'win_rate': win_rate
            }
    
    # 排序并显示
    sorted_sectors = sorted(sector_performance.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    for sector, perf in sorted_sectors:
        pnl_class = "🟢" if perf['total_pnl'] > 0 else "🔴"
        print(f"{pnl_class} {sector}: {perf['trades']}笔, 总盈亏 ¥{perf['total_pnl']:,.0f}, "
              f"胜率 {perf['win_rate']*100:.0f}%, 平均 ¥{perf['avg_pnl']:,.0f}")
    
    return results


def run_optimization():
    """参数优化"""
    print("=" * 70)
    print("🔧 参数优化")
    print("=" * 70)
    
    all_stocks = get_sector_stocks()
    engine = EnhancedBacktest()
    
    # 加载数据
    data = engine.load_data(all_stocks, days=90)
    
    if not data:
        print("❌ 没有加载数据")
        return
    
    # 参数组合
    params = [
        {'top_n': 3, 'min_score': 0.3, 'position_size': 0.2},
        {'top_n': 5, 'min_score': 0.2, 'position_size': 0.15},
        {'top_n': 5, 'min_score': 0.1, 'position_size': 0.15},
        {'top_n': 8, 'min_score': 0.15, 'position_size': 0.12},
        {'top_n': 8, 'min_score': 0.1, 'position_size': 0.1},
    ]
    
    print(f"\n📋 测试 {len(params)} 组参数...\n")
    
    best_result = None
    best_pnl = -float('inf')
    
    for i, param in enumerate(params):
        print(f"--- 参数组 {i+1}/{len(params)}: top_n={param['top_n']}, min_score={param['min_score']}, position={param['position_size']} ---")
        
        results = engine.run_backtest(
            data,
            strategy="multi_factor",
            position_size=param['position_size'],
            max_positions=param['top_n'],
            top_n=param['top_n'],
            min_score=param['min_score']
        )
        
        if results['pnl'] > best_pnl:
            best_pnl = results['pnl']
            best_result = results
            best_param = param
        
        print(f"  收益: {results['pnl_rate']*100:.2f}%, 胜率: {results['win_rate']*100:.0f}%, 夏普: {results['sharpe_ratio']:.2f}")
    
    print("\n" + "=" * 70)
    print("🏆 最优参数")
    print("=" * 70)
    print(f"参数: {best_param}")
    print(f"收益: {best_result['pnl_rate']*100:.2f}%")
    print(f"胜率: {best_result['win_rate']*100:.0f}%")
    print(f"夏普: {best_result['sharpe_ratio']:.2f}")
    print(f"最大回撤: {best_result['max_drawdown']*100:.2f}%")
    
    return best_result, best_param


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=90, help='回测天数')
    parser.add_argument('--top-n', type=int, default=5, help='选股数量')
    parser.add_argument('--min-score', type=float, default=0.15, help='最低因子得分')
    parser.add_argument('--optimize', action='store_true', help='参数优化模式')
    args = parser.parse_args()
    
    if args.optimize:
        run_optimization()
    else:
        run_expanded_backtest(days=args.days, top_n=args.top_n, min_score=args.min_score)
