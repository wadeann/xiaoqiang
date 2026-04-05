#!/usr/bin/env python3
"""
小强量化系统 - 自主回测训练
不依赖 qlib 内置数据，使用本地数据进行因子训练
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data" / "qlib_data"
RESULT_DIR = Path(__file__).parent.parent / "training" / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)


def load_stock_data(symbol: str) -> pd.DataFrame:
    """加载股票数据"""
    file_path = DATA_DIR / f"{symbol}.csv"
    if not file_path.exists():
        return None
    
    df = pd.read_csv(file_path)
    
    # 标准化列名
    if 'Date' in df.columns:
        df = df.rename(columns={'Date': 'date'})
    if 'Close' in df.columns:
        df = df.rename(columns={'Close': 'close'})
    if 'Open' in df.columns:
        df = df.rename(columns={'Open': 'open'})
    if 'High' in df.columns:
        df = df.rename(columns={'High': 'high'})
    if 'Low' in df.columns:
        df = df.rename(columns={'Low': 'low'})
    if 'Volume' in df.columns:
        df = df.rename(columns={'Volume': 'volume'})
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    return df


def calculate_factors(df: pd.DataFrame) -> pd.DataFrame:
    """计算因子"""
    df = df.copy()
    
    # 动量因子
    df['return_1d'] = df['close'].pct_change(1)
    df['return_5d'] = df['close'].pct_change(5)
    df['return_10d'] = df['close'].pct_change(10)
    df['return_20d'] = df['close'].pct_change(20)
    
    # 移动平均
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    # 相对位置
    df['price_ma5_ratio'] = df['close'] / df['ma5'] - 1
    df['price_ma10_ratio'] = df['close'] / df['ma10'] - 1
    df['price_ma20_ratio'] = df['close'] / df['ma20'] - 1
    
    # 波动率
    df['volatility_5d'] = df['return_1d'].rolling(5).std()
    df['volatility_20d'] = df['return_1d'].rolling(20).std()
    
    # 量比
    df['volume_ma5'] = df['volume'].rolling(5).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma5']
    
    # RSI
    def rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    df['rsi_14'] = rsi(df['close'], 14)
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 布林带
    df['boll_mid'] = df['close'].rolling(20).mean()
    df['boll_std'] = df['close'].rolling(20).std()
    df['boll_upper'] = df['boll_mid'] + 2 * df['boll_std']
    df['boll_lower'] = df['boll_mid'] - 2 * df['boll_std']
    df['boll_position'] = (df['close'] - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'])
    
    # 未来收益 (标签)
    df['future_1d_return'] = df['close'].shift(-1) / df['close'] - 1
    df['future_5d_return'] = df['close'].shift(-5) / df['close'] - 1
    
    return df


def analyze_factor(df: pd.DataFrame, factor_name: str) -> dict:
    """分析因子有效性"""
    df = df.dropna(subset=[factor_name, 'future_1d_return', 'future_5d_return'])
    
    if len(df) < 30:
        return None
    
    # 相关性分析
    corr_1d = df[factor_name].corr(df['future_1d_return'])
    corr_5d = df[factor_name].corr(df['future_5d_return'])
    
    # 分组收益分析
    df['factor_group'] = pd.qcut(df[factor_name], 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    group_returns = df.groupby('factor_group')['future_1d_return'].mean()
    
    # IC (Information Coefficient)
    df = df.copy()
    df['date_val'] = pd.to_datetime(df['date'], utc=True).dt.date
    ic_series = df.groupby('date_val').apply(
        lambda x: x[factor_name].corr(x['future_1d_return'])
    )
    ic_mean = ic_series.mean()
    ic_std = ic_series.std()
    icir = ic_mean / ic_std if ic_std != 0 else 0
    
    return {
        'factor': factor_name,
        'samples': len(df),
        'corr_1d': corr_1d,
        'corr_5d': corr_5d,
        'ic_mean': ic_mean,
        'ic_std': ic_std,
        'icir': icir,
        'group_returns': group_returns.to_dict(),
    }


def train_and_evaluate():
    """训练并评估因子"""
    print("=" * 60)
    print("🧠 小强量化系统 - 因子训练")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 加载所有股票数据
    all_data = {}
    for file in DATA_DIR.glob("*.csv"):
        symbol = file.stem
        df = load_stock_data(symbol)
        if df is not None and len(df) > 30:
            df = calculate_factors(df)
            all_data[symbol] = df
            print(f"  ✅ {symbol}: {len(df)} 条记录")
    
    if not all_data:
        print("❌ 无有效数据")
        return
    
    print(f"\n📊 加载 {len(all_data)} 只标的")
    
    # 合并所有数据
    all_df = pd.concat(all_data.values(), keys=all_data.keys(), names=['symbol', 'idx'])
    all_df = all_df.reset_index(drop=True)
    
    # 要分析的因子
    factors = [
        'return_1d', 'return_5d', 'return_10d', 'return_20d',
        'price_ma5_ratio', 'price_ma10_ratio', 'price_ma20_ratio',
        'volatility_5d', 'volatility_20d',
        'volume_ratio',
        'rsi_14',
        'macd', 'macd_hist',
        'boll_position',
    ]
    
    # 分析每个因子
    print("\n📈 因子分析结果:")
    print("-" * 80)
    print(f"{'因子':<20} {'样本数':<10} {'IC均值':<12} {'ICIR':<10} {'1日相关':<12} {'5日相关':<12}")
    print("-" * 80)
    
    results = []
    for factor in factors:
        if factor not in all_df.columns:
            continue
        
        result = analyze_factor(all_df, factor)
        if result:
            results.append(result)
            print(f"{factor:<20} {result['samples']:<10} {result['ic_mean']:<12.4f} {result['icir']:<10.4f} {result['corr_1d']:<12.4f} {result['corr_5d']:<12.4f}")
    
    print("-" * 80)
    
    # 排序并推荐
    results.sort(key=lambda x: abs(x['ic_mean']), reverse=True)
    
    print("\n🏆 Top 5 有效因子:")
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. {r['factor']}: IC={r['ic_mean']:.4f}, ICIR={r['icir']:.4f}")
    
    # 保存结果
    result_file = RESULT_DIR / f"factor_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✅ 结果已保存: {result_file}")
    
    # 生成因子推荐
    print("\n💡 因子推荐:")
    top_factors = [r['factor'] for r in results[:5] if abs(r['ic_mean']) > 0.02]
    if top_factors:
        print(f"  建议使用因子: {', '.join(top_factors)}")
    else:
        print("  当前因子效果较弱，建议开发新因子")
    
    return results


if __name__ == "__main__":
    train_and_evaluate()
