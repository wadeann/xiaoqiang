#!/usr/bin/env python3
"""
小强量化系统 - 翻倍股特征分析与潜力股挖掘
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


class DragonAnalyzer:
    """翻倍股特征分析器"""
    
    def __init__(self):
        self.loader = DataLoader()
    
    def analyze_doublers(self, symbols, days=180):
        """分析翻倍股特征"""
        print("=" * 80)
        print("📊 翻倍股特征分析")
        print("=" * 80)
        
        results = []
        
        for symbol in symbols:
            try:
                df = self.loader.load_a_share_history(symbol, days=days)
                if df is None or len(df) < days * 0.8:
                    continue
                
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                
                # 基础指标
                start_price = df['close'].iloc[0]
                end_price = df['close'].iloc[-1]
                max_price = df['close'].max()
                min_price = df['close'].min()
                
                total_return = (end_price - start_price) / start_price * 100
                max_return = (max_price - start_price) / start_price * 100
                
                if total_return < 50:  # 只分析强势股
                    continue
                
                # ========== 关键特征 ==========
                
                # 1. 启动特征 (前30天)
                early_30 = df.iloc[:30]
                early_return = (early_30['close'].iloc[-1] - early_30['close'].iloc[0]) / early_30['close'].iloc[0] * 100
                early_volume_ratio = early_30['volume'].mean() / df['volume'].iloc[:60].mean()
                
                # 2. 突破特征 (成交量放大)
                volume_ma = df['volume'].rolling(20).mean()
                breakout_days = (df['volume'] > volume_ma * 2).sum()
                volume_surge_ratio = df['volume'].max() / df['volume'].mean()
                
                # 3. 趋势特征
                df['ma5'] = df['close'].rolling(5).mean()
                df['ma10'] = df['close'].rolling(10).mean()
                df['ma20'] = df['close'].rolling(20).mean()
                df['ma60'] = df['close'].rolling(60).mean()
                
                # 多头排列天数
                bullish_days = ((df['ma5'] > df['ma10']) & (df['ma10'] > df['ma20'])).sum()
                bullish_ratio = bullish_days / len(df) * 100
                
                # 4. 动量特征
                df['return'] = df['close'].pct_change()
                df['momentum_5'] = df['close'].pct_change(5) * 100
                df['momentum_20'] = df['close'].pct_change(20) * 100
                
                # 连续上涨
                df['up'] = (df['close'] > df['close'].shift(1)).astype(int)
                max_consecutive_up = 0
                current = 0
                for v in df['up']:
                    current = current + 1 if v else 0
                    max_consecutive_up = max(max_consecutive_up, current)
                
                # 5. 波动特征
                volatility = df['return'].std() * np.sqrt(252) * 100
                max_drawdown = (df['close'].cummax() - df['close']).max() / df['close'].cummax().max() * 100
                
                # 6. RSI 特征
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / (loss + 1e-6)
                df['rsi'] = 100 - (100 / (1 + rs))
                
                rsi_start = df['rsi'].iloc[:30].mean()
                rsi_breakout = df['rsi'].loc[df['close'] == max_price].iloc[0] if len(df.loc[df['close'] == max_price]) > 0 else 70
                
                # 7. 板块特征
                sector = self._get_sector(symbol)
                
                # 8. 时间特征 (从启动到最高点的时间)
                max_idx = df['close'].idxmax()
                days_to_max = df.index.get_loc(max_idx) if max_idx in df.index else 0
                
                results.append({
                    'symbol': symbol,
                    'sector': sector,
                    'total_return': total_return,
                    'max_return': max_return,
                    'early_return': early_return,
                    'early_volume_ratio': early_volume_ratio,
                    'breakout_days': breakout_days,
                    'volume_surge_ratio': volume_surge_ratio,
                    'bullish_ratio': bullish_ratio,
                    'max_consecutive_up': max_consecutive_up,
                    'volatility': volatility,
                    'max_drawdown': max_drawdown,
                    'rsi_start': rsi_start,
                    'rsi_breakout': rsi_breakout,
                    'days_to_max': days_to_max,
                })
                
            except Exception as e:
                pass
        
        return pd.DataFrame(results)
    
    def _get_sector(self, symbol):
        """获取板块"""
        sectors = {
            '300308.SZ': '光模块', '300394.SZ': '光模块', '300502.SZ': '光模块',
            '688205.SH': '光模块', '688195.SH': '光模块', '002281.SZ': '光模块',
            '688307.SH': '光模块', '300570.SZ': '光模块',
            '688256.SH': 'AI芯片', '688041.SH': 'AI芯片', '300474.SZ': 'AI芯片',
            '688012.SH': '半导体设备', '688120.SH': '半导体设备', '002371.SZ': '半导体设备',
            '688008.SH': '半导体设备', '300661.SZ': '半导体设备',
            '002812.SZ': '新能源', '300274.SZ': '新能源', '300750.SZ': '新能源',
            '002594.SZ': '新能源', '601012.SH': '新能源',
            '300024.SZ': '机器人', '002747.SZ': '机器人', '300124.SZ': '机器人',
        }
        return sectors.get(symbol, '其他')
    
    def print_analysis(self, df):
        """打印分析结果"""
        if df.empty:
            print("无数据")
            return
        
        print(f"\n📊 翻倍股总数: {len(df)} 只")
        print("-" * 80)
        
        # 板块分析
        print("\n🏭 板块分布:")
        print("-" * 80)
        sector_stats = df.groupby('sector').agg({
            'total_return': ['mean', 'max'],
            'symbol': 'count'
        }).round(1)
        sector_stats.columns = ['平均涨幅%', '最大涨幅%', '数量']
        sector_stats = sector_stats.sort_values('平均涨幅%', ascending=False)
        print(sector_stats.to_string())
        
        # 关键特征分析
        print("\n📈 翻倍股关键特征 (平均值):")
        print("-" * 80)
        features = {
            '启动30天涨幅': f"{df['early_return'].mean():.1f}%",
            '启动期成交量放大': f"{df['early_volume_ratio'].mean():.2f}x",
            '突破天数(量>2倍均量)': f"{df['breakout_days'].mean():.0f}天",
            '成交量爆发比': f"{df['volume_surge_ratio'].mean():.1f}x",
            '多头排列比例': f"{df['bullish_ratio'].mean():.1f}%",
            '最大连续上涨': f"{df['max_consecutive_up'].mean():.1f}天",
            '年化波动率': f"{df['volatility'].mean():.1f}%",
            '最大回撤': f"{df['max_drawdown'].mean():.1f}%",
            '启动RSI': f"{df['rsi_start'].mean():.0f}",
            '突破时RSI': f"{df['rsi_breakout'].mean():.0f}",
            '涨到最高点天数': f"{df['days_to_max'].mean():.0f}天",
        }
        for k, v in features.items():
            print(f"  {k}: {v}")
        
        # 个股详情
        print("\n🏆 个股详细分析:")
        print("-" * 80)
        print(f"{'股票':<12} {'板块':<10} {'涨幅':>8} {'启动涨幅':>10} {'量爆比':>8} {'多头比例':>10} {'连续上涨':>8}")
        print("-" * 80)
        for _, row in df.sort_values('total_return', ascending=False).iterrows():
            print(f"{row['symbol']:<12} {row['sector']:<10} {row['total_return']:>7.1f}% {row['early_return']:>9.1f}% "
                  f"{row['volume_surge_ratio']:>7.1f}x {row['bullish_ratio']:>9.1f}% {row['max_consecutive_up']:>7}天")
    
    def find_potential(self, symbols, days=60):
        """挖掘潜力股 - 当前刚起步"""
        print("\n" + "=" * 80)
        print("🔍 潜力股挖掘 - 当前刚起步特征")
        print("=" * 80)
        
        results = []
        
        for symbol in symbols:
            try:
                df = self.loader.load_a_share_history(symbol, days=days)
                if df is None or len(df) < days * 0.8:
                    continue
                
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                
                # 计算指标
                df['ma5'] = df['close'].rolling(5).mean()
                df['ma10'] = df['close'].rolling(10).mean()
                df['ma20'] = df['close'].rolling(20).mean()
                
                # RSI
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / (loss + 1e-6)
                df['rsi'] = 100 - (100 / (1 + rs))
                
                # 动量
                df['momentum_5'] = df['close'].pct_change(5) * 100
                df['momentum_10'] = df['close'].pct_change(10) * 100
                
                # 成交量
                df['volume_ma'] = df['volume'].rolling(20).mean()
                df['volume_ratio'] = df['volume'] / df['volume_ma']
                
                # 最新数据
                latest = df.iloc[-1]
                
                # ===== 翻倍股启动特征 =====
                
                # 特征1: 启动期涨幅 (最近5天涨幅 > 5%)
                recent_5d_return = (latest['close'] - df['close'].iloc[-6]) / df['close'].iloc[-6] * 100 if len(df) >= 6 else 0
                
                # 特征2: 成交量放大 (最近成交量 > 2倍均量)
                recent_volume_surge = df['volume_ratio'].iloc[-5:].mean() > 1.5
                
                # 特征3: 刚刚突破 MA20
                just_break_ma20 = latest['close'] > latest['ma20'] and df['close'].iloc[-10] < df['ma20'].iloc[-10]
                
                # 特征4: RSI 从超卖区上升 (RSI 40-60)
                rsi_ok = 40 < latest['rsi'] < 65
                
                # 特征5: 动量向上
                momentum_ok = latest['momentum_5'] > 0 and latest['momentum_10'] > 0
                
                # 特征6: 多头排列刚开始
                bullish_start = (latest['ma5'] > latest['ma10']) and not (df['ma5'].iloc[-10] > df['ma10'].iloc[-10])
                
                # 综合得分
                score = 0
                if recent_5d_return > 5: score += 2
                elif recent_5d_return > 3: score += 1
                
                if recent_volume_surge: score += 2
                if just_break_ma20: score += 2
                if rsi_ok: score += 1
                if momentum_ok: score += 1
                if bullish_start: score += 2
                
                # 板块
                sector = self._get_sector(symbol)
                
                if score >= 4:  # 只保留得分 >= 4 的
                    results.append({
                        'symbol': symbol,
                        'sector': sector,
                        'close': latest['close'],
                        'recent_5d_return': recent_5d_return,
                        'volume_ratio': df['volume_ratio'].iloc[-1],
                        'rsi': latest['rsi'],
                        'momentum_5': latest['momentum_5'],
                        'ma20': latest['ma20'],
                        'score': score,
                        'break_ma20': just_break_ma20,
                        'volume_surge': recent_volume_surge,
                    })
                
            except Exception as e:
                pass
        
        potential_df = pd.DataFrame(results)
        
        if potential_df.empty:
            print("⚠️ 当前未发现符合条件的潜力股")
            return potential_df
        
        # 排序
        potential_df = potential_df.sort_values('score', ascending=False)
        
        print(f"\n🎯 发现 {len(potential_df)} 只潜力股:")
        print("-" * 80)
        print(f"{'股票':<12} {'板块':<10} {'价格':>8} {'5日涨幅':>8} {'量比':>6} {'RSI':>5} {'得分':>5}")
        print("-" * 80)
        
        for _, row in potential_df.head(20).iterrows():
            print(f"{row['symbol']:<12} {row['sector']:<10} {row['close']:>8.2f} {row['recent_5d_return']:>7.1f}% "
                  f"{row['volume_ratio']:>5.1f}x {row['rsi']:>5.0f} {row['score']:>5}")
        
        # 板块汇总
        print("\n📊 潜力板块分布:")
        print("-" * 80)
        sector_count = potential_df['sector'].value_counts()
        for sector, count in sector_count.items():
            avg_score = potential_df[potential_df['sector'] == sector]['score'].mean()
            print(f"  {sector}: {count} 只, 平均得分 {avg_score:.1f}")
        
        return potential_df


# 扩展股票池 - 包含更多板块
ALL_STOCKS = [
    # 光模块/光通信
    '300308.SZ', '300394.SZ', '300502.SZ', '002281.SZ', '688205.SH', '688195.SH',
    '688307.SH', '300570.SZ', '603118.SH',
    
    # AI芯片
    '300474.SZ', '688981.SH', '688256.SH', '688041.SH', '002049.SZ',
    
    # 半导体设备
    '603501.SH', '002371.SZ', '300661.SZ', '688012.SH', '688120.SH', '688008.SH',
    '688147.SH', '688037.SH',
    
    # 新能源
    '300750.SZ', '002594.SZ', '002812.SZ', '300014.SZ', '601012.SH', '300274.SZ',
    '688599.SH', '688303.SH', '600438.SH',
    
    # 机器人
    '300024.SZ', '002747.SZ', '300124.SZ', '688169.SH',
    
    # 消费电子
    '002475.SZ', '000725.SZ', '002241.SZ', '603160.SH',
    
    # 医药
    '300760.SZ', '300122.SZ', '300015.SZ', '688180.SH',
    
    # 金融科技
    '300033.SZ', '600570.SH',
    
    # 更多半导体
    '688396.SH', '688521.SH', '002156.SZ', '300236.SZ',
]


if __name__ == "__main__":
    analyzer = DragonAnalyzer()
    
    # 1. 分析翻倍股特征
    doublers_df = analyzer.analyze_doublers(ALL_STOCKS, days=180)
    analyzer.print_analysis(doublers_df)
    
    # 保存结果
    doublers_df.to_csv('reports/dragon_analysis.csv', index=False)
    print(f"\n📁 分析结果已保存到 reports/dragon_analysis.csv")
    
    # 2. 挖掘潜力股
    print("\n" + "=" * 80)
    print("🔍 开始挖掘当前潜力股...")
    print("=" * 80)
    
    potential_df = analyzer.find_potential(ALL_STOCKS, days=60)
    
    if not potential_df.empty:
        potential_df.to_csv('reports/potential_stocks.csv', index=False)
        print(f"\n📁 潜力股列表已保存到 reports/potential_stocks.csv")
