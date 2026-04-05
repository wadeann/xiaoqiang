#!/usr/bin/env python3
"""
小强量化系统 - 龙头股轮动分析与估值空间评估
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

for proxy in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(proxy, None)

sys.path.insert(0, str(Path(__file__).parent.parent))
from backtest.run_backtest import DataLoader


class DragonRotationAnalyzer:
    """龙头股轮动分析器"""
    
    def __init__(self):
        self.loader = DataLoader()
    
    def analyze_rotation(self, symbols, days=400):
        """分析龙头股轮动规律"""
        print("=" * 90)
        print("📊 龙头股轮动分析 - 从中际旭创到德科立")
        print("=" * 90)
        
        all_data = {}
        
        # 加载所有数据
        for symbol in symbols:
            try:
                df = self.loader.load_a_share_history(symbol, days=days)
                if df is not None and len(df) >= days * 0.8:
                    df['close'] = pd.to_numeric(df['close'], errors='coerce')
                    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                    all_data[symbol] = df
                    print(f"  ✅ {symbol}: {len(df)} 天数据")
            except:
                pass
        
        if not all_data:
            print("❌ 无法加载数据")
            return
        
        print("\n" + "=" * 90)
        print("📈 各阶段龙头分析")
        print("=" * 90)
        
        # 定义时间段
        periods = [
            ("2025-01", "2025-06", "第一阶段 (2025H1)"),
            ("2025-06", "2025-09", "第二阶段 (2025Q3)"),
            ("2025-09", "2025-12", "第三阶段 (2025Q4)"),
            ("2026-01", "2026-04", "第四阶段 (2026Q1)"),
        ]
        
        # 按阶段分析
        stage_leaders = []
        
        for start, end, name in periods:
            print(f"\n{'='*90}")
            print(f"📅 {name}")
            print(f"{'='*90}")
            
            period_results = []
            
            for symbol, df in all_data.items():
                try:
                    # 过滤时间段
                    df['date'] = pd.to_datetime(df['date'])
                    mask = (df['date'] >= start) & (df['date'] <= end)
                    period_df = df[mask]
                    
                    if len(period_df) < 30:
                        continue
                    
                    # 计算阶段涨幅
                    start_price = period_df['close'].iloc[0]
                    end_price = period_df['close'].iloc[-1]
                    period_return = (end_price - start_price) / start_price * 100
                    
                    # 最高点
                    max_price = period_df['close'].max()
                    max_return = (max_price - start_price) / start_price * 100
                    
                    # 成交量
                    avg_volume = period_df['volume'].mean()
                    
                    # 成交额
                    avg_amount = period_df['amount'].mean()
                    
                    period_results.append({
                        'symbol': symbol,
                        'period': name,
                        'start': start,
                        'end': end,
                        'period_return': period_return,
                        'max_return': max_return,
                        'avg_volume': avg_volume,
                        'avg_amount': avg_amount,
                    })
                    
                except Exception as e:
                    pass
            
            if period_results:
                # 排序
                period_df = pd.DataFrame(period_results)
                period_df = period_df.sort_values('max_return', ascending=False)
                
                # 显示 Top 5
                print(f"\n{'股票':<12} {'阶段涨幅':>12} {'最高涨幅':>12} {'平均成交额':>15}")
                print("-" * 90)
                
                for i, row in period_df.head(5).iterrows():
                    leader_mark = " 👑" if i == period_df.index[0] else ""
                    print(f"{row['symbol']:<12} {row['period_return']:>11.1f}% {row['max_return']:>11.1f}% {row['avg_amount']/1e8:>14.2f}亿{leader_mark}")
                
                # 记录阶段龙头
                leader = period_df.iloc[0]
                stage_leaders.append({
                    'period': name,
                    'leader': leader['symbol'],
                    'max_return': leader['max_return'],
                    'avg_amount': leader['avg_amount'],
                })
        
        # 打印龙头轮动
        print("\n" + "=" * 90)
        print("👑 龙头轮动时间线")
        print("=" * 90)
        
        for i, leader in enumerate(stage_leaders):
            print(f"{leader['period']}: {leader['leader']} (最高+{leader['max_return']:.1f}%, 成交额{leader['avg_amount']/1e8:.1f}亿)")
        
        return all_data, stage_leaders
    
    def analyze_valuation(self, symbol, days=400):
        """分析个股估值空间"""
        print(f"\n{'='*90}")
        print(f"📊 {symbol} 估值空间分析")
        print(f"{'='*90}")
        
        df = self.loader.load_a_share_history(symbol, days=days)
        if df is None:
            print("❌ 无法加载数据")
            return None
        
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # 计算关键指标
        current_price = df['close'].iloc[-1]
        min_price = df['close'].min()
        max_price = df['close'].max()
        
        # 从最低点涨幅
        gain_from_low = (current_price - min_price) / min_price * 100
        # 距离最高点
        drop_from_high = (max_price - current_price) / max_price * 100
        
        # 历史分位数
        price_percentile = (df['close'] < current_price).sum() / len(df) * 100
        
        # 成交额趋势
        df['amount_ma20'] = df['amount'].rolling(20).mean()
        recent_amount = df['amount'].iloc[-20:].mean()
        overall_amount = df['amount'].mean()
        volume_trend = recent_amount / overall_amount
        
        # 估值指标
        print(f"\n当前价格: ¥{current_price:.2f}")
        print(f"历史最低: ¥{min_price:.2f} (从最低点涨幅: +{gain_from_low:.1f}%)")
        print(f"历史最高: ¥{max_price:.2f} (距最高点: -{drop_from_high:.1f}%)")
        print(f"价格分位: {price_percentile:.1f}% (当前价格在历史{price_percentile:.0f}%分位)")
        print(f"成交额趋势: {volume_trend:.2f}x (近期/平均)")
        
        # 计算各阶段涨幅
        df['date'] = pd.to_datetime(df['date'])
        
        stages = [
            ("过去30天", 30),
            ("过去60天", 60),
            ("过去90天", 90),
            ("过去180天", 180),
            ("过去365天", 365),
            ("全部数据", len(df)),
        ]
        
        print(f"\n{'阶段':<15} {'起始价':>10} {'结束价':>10} {'涨幅':>10} {'最高涨幅':>12}")
        print("-" * 90)
        
        for name, days in stages:
            if len(df) >= days:
                stage_df = df.iloc[-days:]
                start_price = stage_df['close'].iloc[0]
                end_price = stage_df['close'].iloc[-1]
                max_price = stage_df['close'].max()
                stage_return = (end_price - start_price) / start_price * 100
                max_return = (max_price - start_price) / start_price * 100
                print(f"{name:<15} ¥{start_price:>9.2f} ¥{end_price:>9.2f} {stage_return:>9.1f}% {max_return:>11.1f}%")
        
        # 上涨空间评估
        print(f"\n{'='*90}")
        print("📈 上涨空间评估")
        print("=" * 90)
        
        # 基于历史涨幅推算
        if gain_from_low < 100:
            print(f"🟢 早期阶段：从低点涨幅仅 {gain_from_low:.1f}%，处于上涨初期")
            print(f"   翻倍龙头平均涨幅 200-700%，上涨空间: {200 - gain_from_low:.0f}% - {700 - gain_from_low:.0f}%")
        elif gain_from_low < 300:
            print(f"🟡 中期阶段：从低点涨幅 {gain_from_low:.1f}%，处于主升浪")
            print(f"   参考历史龙头，可能还有 {300 - gain_from_low:.0f}% - {400 - gain_from_low:.0f}% 空间")
        elif gain_from_low < 500:
            print(f"🟠 后期阶段：从低点涨幅 {gain_from_low:.1f}%，接近历史高位")
            print(f"   注意风险，空间有限，建议移动止损")
        else:
            print(f"🔴 高位阶段：从低点涨幅 {gain_from_low:.1f}%，处于高位")
            print(f"   估值较高，建议谨慎或止盈")
        
        # 成交额分析
        print(f"\n{'='*90}")
        print("💰 资金分析")
        print("=" * 90)
        
        if volume_trend > 1.5:
            print(f"✅ 资金持续流入：近期成交额是平均的 {volume_trend:.1f}x")
        elif volume_trend > 1.0:
            print(f"📊 资金平稳：近期成交额是平均的 {volume_trend:.1f}x")
        else:
            print(f"⚠️ 资金萎缩：近期成交额是平均的 {volume_trend:.1f}x")
        
        return df
    
    def compare_dragons(self, old_leader, new_leader, days=400):
        """对比分析龙头切换"""
        print(f"\n{'='*90}")
        print(f"🔄 龙头切换分析: {old_leader} → {new_leader}")
        print(f"{'='*90}")
        
        # 加载数据
        old_df = self.loader.load_a_share_history(old_leader, days=days)
        new_df = self.loader.load_a_share_history(new_leader, days=days)
        
        if old_df is None or new_df is None:
            print("❌ 无法加载数据")
            return
        
        old_df['close'] = pd.to_numeric(old_df['close'], errors='coerce')
        old_df['amount'] = pd.to_numeric(old_df['amount'], errors='coerce')
        new_df['close'] = pd.to_numeric(new_df['close'], errors='coerce')
        new_df['amount'] = pd.to_numeric(new_df['amount'], errors='coerce')
        
        # 计算对比指标
        print(f"\n{'指标':<25} {old_leader:<20} {new_leader:<20} {'差异':>15}")
        print("-" * 90)
        
        # 涨幅对比
        old_return = (old_df['close'].iloc[-1] / old_df['close'].iloc[0] - 1) * 100
        new_return = (new_df['close'].iloc[-1] / new_df['close'].iloc[0] - 1) * 100
        print(f"{'总涨幅':<25} {old_return:>19.1f}% {new_return:>19.1f}% {new_return - old_return:>14.1f}%")
        
        # 成交额对比
        old_amount = old_df['amount'].mean() / 1e8
        new_amount = new_df['amount'].mean() / 1e8
        print(f"{'平均成交额(亿)':<25} {old_amount:>19.2f} {new_amount:>19.2f} {(new_amount/old_amount-1)*100:>14.1f}%")
        
        # 最高涨幅
        old_max = (old_df['close'].max() / old_df['close'].iloc[0] - 1) * 100
        new_max = (new_df['close'].max() / new_df['close'].iloc[0] - 1) * 100
        print(f"{'最高涨幅':<25} {old_max:>19.1f}% {new_max:>19.1f}% {new_max - old_max:>14.1f}%")
        
        # 当前价格分位
        old_pct = (old_df['close'] < old_df['close'].iloc[-1]).sum() / len(old_df) * 100
        new_pct = (new_df['close'] < new_df['close'].iloc[-1]).sum() / len(new_df) * 100
        print(f"{'价格分位':<25} {old_pct:>19.1f}% {new_pct:>19.1f}% {new_pct - old_pct:>14.1f}%")
        
        # 最近60天涨幅
        old_recent = (old_df['close'].iloc[-1] / old_df['close'].iloc[-60] - 1) * 100 if len(old_df) >= 60 else 0
        new_recent = (new_df['close'].iloc[-1] / new_df['close'].iloc[-60] - 1) * 100 if len(new_df) >= 60 else 0
        print(f"{'近60天涨幅':<25} {old_recent:>19.1f}% {new_recent:>19.1f}% {new_recent - old_recent:>14.1f}%")
        
        # 切换原因分析
        print(f"\n{'='*90}")
        print("🔍 切换原因分析")
        print("=" * 90)
        
        if new_recent > old_recent * 1.5:
            print(f"✅ 动能更强：{new_leader} 近期涨幅 {new_recent:.1f}% > {old_leader} {old_recent:.1f}%")
        
        if new_amount > old_amount * 1.3:
            print(f"✅ 资金更活跃：{new_leader} 成交额 {new_amount:.1f}亿 > {old_leader} {old_amount:.1f}亿")
        
        if new_pct < old_pct - 10:
            print(f"✅ 估值更低：{new_leader} 价格分位 {new_pct:.0f}% < {old_leader} {old_pct:.0f}%")
        
        if new_max < old_max * 0.8:
            print(f"✅ 空间更大：{new_leader} 最高涨幅 {new_max:.1f}% 还有空间追赶")


# 光模块龙头股
OPTICAL_STOCKS = [
    '300308.SZ',  # 中际旭创 - 前龙头
    '300394.SZ',  # 天孚通信
    '300502.SZ',  # 新易盛
    '688205.SH',  # 德科立 - 新龙头
    '688195.SH',  # 腾景科技 - 最强
    '002281.SZ',  # 光迅科技
    '688307.SH',  # 中润光学
    '300570.SH',  # 太辰光
]


if __name__ == "__main__":
    analyzer = DragonRotationAnalyzer()
    
    # 1. 龙头轮动分析
    all_data, stage_leaders = analyzer.analyze_rotation(OPTICAL_STOCKS, days=400)
    
    # 2. 德科立估值分析
    print("\n" + "=" * 90)
    print("🎯 重点分析：德科立 (688205.SH)")
    print("=" * 90)
    analyzer.analyze_valuation('688205.SH', days=400)
    
    # 3. 腾景科技估值分析
    print("\n" + "=" * 90)
    print("🎯 重点分析：腾景科技 (688195.SH)")
    print("=" * 90)
    analyzer.analyze_valuation('688195.SH', days=400)
    
    # 4. 中际旭创估值分析
    print("\n" + "=" * 90)
    print("🎯 重点分析：中际旭创 (300308.SZ)")
    print("=" * 90)
    analyzer.analyze_valuation('300308.SZ', days=400)
    
    # 5. 龙头切换对比
    analyzer.compare_dragons('300308.SZ', '688205.SH', days=400)
    analyzer.compare_dragons('300308.SZ', '688195.SH', days=400)
