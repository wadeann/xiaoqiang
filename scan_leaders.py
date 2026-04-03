#!/usr/bin/env python3
"""
小强量化系统 - A股龙头潜力股扫描器
扫描全市场，找出龙头潜力股
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.a_share_data import AShareDataFetcher
from datetime import datetime


def scan_leaders():
    """扫描龙头潜力股"""
    fetcher = AShareDataFetcher()
    
    print("=" * 70)
    print("🐉 A股龙头潜力股扫描")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 获取市场概况
    print("📊 市场概况:")
    summary = fetcher.get_market_summary()
    for name, data in summary.items():
        emoji = "🟢" if data['change_pct'] > 0 else "🔴"
        print(f"  {emoji} {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)")
    print()
    
    # 2. 扩展股票池 - AI/半导体核心标的
    extended_pool = [
        # AI 芯片
        "300474.SZ",  # 景嘉微
        "688981.SH",  # 中芯国际
        "002049.SZ",  # 紫光国微
        "688256.SH",  # 寒武纪
        "688041.SH",  # 海光信息
        "688396.SH",  # 华润微
        
        # AI 算力
        "000977.SZ",  # 浪潮信息
        "002230.SZ",  # 科大讯飞
        "300033.SZ",  # 同花顺
        "688111.SH",  # 金山办公
        "002405.SZ",  # 四维图新
        
        # 半导体设备
        "603501.SH",  # 韦尔股份
        "002371.SZ",  # 北方华创
        "300661.SZ",  # 圣邦股份
        "688012.SH",  # 中微公司
        "688521.SH",  # 芯源微
        "688147.SH",  # 盛美上海
        
        # 存储芯片
        "603501.SH",  # 韦尔股份
        "002049.SZ",  # 紫光国微
        "688008.SH",  # 澜起科技
        
        # 新能源
        "300750.SZ",  # 宁德时代
        "002594.SZ",  # 比亚迪
        "600309.SH",  # 万华化学
        
        # 消费电子
        "002475.SZ",  # 立讯精密
        "002241.SZ",  # 歌尔股份
        
        # 军工
        "600893.SH",  # 航发动力
        "002179.SZ",  # 中航光电
    ]
    
    # 去重
    extended_pool = list(set(extended_pool))
    
    print(f"📈 扫描股票池: {len(extended_pool)} 只")
    print()
    
    # 3. 获取行情
    print("📊 获取实时行情...")
    quotes = fetcher.scan_all(extended_pool)
    
    if not quotes:
        print("❌ 无法获取行情数据")
        return
    
    print(f"✅ 成功获取 {len(quotes)} 只股票行情")
    print()
    
    # 4. 分析龙头潜力
    print("=" * 70)
    print("🐉 龙头潜力股分析")
    print("=" * 70)
    
    # 按涨幅排序
    sorted_quotes = sorted(quotes.items(), key=lambda x: x[1].get('change_pct', 0), reverse=True)
    
    # 找出强势股 (涨幅>0)
    strong_stocks = [(s, q) for s, q in sorted_quotes if q.get('change_pct', 0) > 0]
    
    # 找出抗跌股 (跌幅<市场平均)
    avg_change = sum(q.get('change_pct', 0) for q in quotes.values()) / len(quotes)
    resistant_stocks = [(s, q) for s, q in sorted_quotes if q.get('change_pct', 0) > avg_change and q.get('change_pct', 0) < 0]
    
    # 找出高换手率
    high_turnover = [(s, q) for s, q in sorted_quotes if q.get('turnover', 0) > 5]
    high_turnover.sort(key=lambda x: x[1].get('turnover', 0), reverse=True)
    
    # 5. 输出结果
    print()
    print("🟢 强势股 (上涨):")
    if strong_stocks:
        for i, (symbol, quote) in enumerate(strong_stocks[:10], 1):
            name = quote.get('name', '')
            price = quote.get('price', 0)
            change = quote.get('change_pct', 0)
            turnover = quote.get('turnover', 0)
            print(f"  {i}. {name}({symbol}): ¥{price:.2f} ({change:+.2f}%) 换手{turnover:.1f}%")
    else:
        print("  今日无强势股")
    
    print()
    print("💪 抗跌龙头 (跌幅小于市场平均):")
    if resistant_stocks:
        for i, (symbol, quote) in enumerate(resistant_stocks[:10], 1):
            name = quote.get('name', '')
            price = quote.get('price', 0)
            change = quote.get('change_pct', 0)
            print(f"  {i}. {name}({symbol}): ¥{price:.2f} ({change:+.2f}%) vs 市场{avg_change:.2f}%")
    else:
        print("  今日无抗跌股")
    
    print()
    print("🔥 高换手率 (换手>5%):")
    if high_turnover:
        for i, (symbol, quote) in enumerate(high_turnover[:10], 1):
            name = quote.get('name', '')
            price = quote.get('price', 0)
            change = quote.get('change_pct', 0)
            turnover = quote.get('turnover', 0)
            emoji = "🟢" if change > 0 else "🔴"
            print(f"  {i}. {emoji} {name}({symbol}): ¥{price:.2f} ({change:+.2f}%) 换手{turnover:.1f}%")
    else:
        print("  今日无高换手率股票")
    
    # 6. 综合评分
    print()
    print("=" * 70)
    print("⭐ 综合评分 Top 10")
    print("=" * 70)
    
    scores = []
    for symbol, quote in quotes.items():
        score = 0
        change = quote.get('change_pct', 0)
        turnover = quote.get('turnover', 0)
        
        # 涨幅加分
        if change > 5:
            score += 50
        elif change > 3:
            score += 40
        elif change > 1:
            score += 30
        elif change > 0:
            score += 20
        elif change > -1:
            score += 10
        elif change > -3:
            score += 5
        
        # 换手率加分
        if turnover > 10:
            score += 30
        elif turnover > 5:
            score += 20
        elif turnover > 3:
            score += 10
        
        # 抗跌加分 (相对市场)
        if change > avg_change:
            score += 20
        
        scores.append({
            'symbol': symbol,
            'name': quote.get('name', ''),
            'price': quote.get('price', 0),
            'change_pct': change,
            'turnover': turnover,
            'score': score
        })
    
    scores.sort(key=lambda x: x['score'], reverse=True)
    
    for i, s in enumerate(scores[:10], 1):
        emoji = "🟢" if s['change_pct'] > 0 else "🔴" if s['change_pct'] < 0 else "⚪"
        print(f"  {i}. {emoji} {s['name']}({s['symbol']}): ¥{s['price']:.2f} ({s['change_pct']:+.2f}%) 换手{s['turnover']:.1f}% 评分:{s['score']}")
    
    print()
    print("=" * 70)
    print(f"市场平均涨幅: {avg_change:.2f}%")
    print(f"上涨/下跌: {len(strong_stocks)}/{len(quotes) - len(strong_stocks)}")
    print("=" * 70)


if __name__ == "__main__":
    scan_leaders()
