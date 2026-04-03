#!/usr/bin/env python3
"""
小强量化系统 - 热门板块扫描器
动态扫描市场热门板块
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from data.a_share_data import AShareDataFetcher


# 热门板块定义
HOT_SECTORS = {
    "油气": {
        "description": "石油天然气",
        "stocks": [
            "600028.SH",  # 中国石化
            "601857.SH",  # 中国石油
            "601808.SH",  # 中海油服
            "000554.SZ",  # 泰山石油
            "002353.SZ",  # 杰瑞股份
            "603619.SH",  # 中曼石油
            "300157.SZ",  # 恒泰艾普
        ]
    },
    "创新药": {
        "description": "创新药研发",
        "stocks": [
            "300760.SZ",  # 迈瑞医疗
            "603259.SH",  # 药明康德
            "300347.SZ",  # 泰格医药
            "603127.SH",  # 昭衍新药
            "688180.SH",  # 君实生物
            "688235.SH",  # 百济神州
            "300122.SZ",  # 智飞生物
            "002821.SZ",  # 凯莱英
        ]
    },
    "AI算力": {
        "description": "人工智能算力",
        "stocks": [
            "300474.SZ",  # 景嘉微
            "688256.SH",  # 寒武纪
            "688041.SH",  # 海光信息
            "002230.SZ",  # 科大讯飞
            "000977.SZ",  # 浪潮信息
        ]
    },
    "半导体": {
        "description": "芯片设计制造",
        "stocks": [
            "688981.SH",  # 中芯国际
            "002049.SZ",  # 紫光国微
            "603501.SH",  # 韦尔股份
            "002371.SZ",  # 北方华创
            "300661.SZ",  # 圣邦股份
        ]
    },
    "军工": {
        "description": "国防军工",
        "stocks": [
            "600893.SH",  # 航发动力
            "002179.SZ",  # 中航光电
            "600150.SH",  # 中国船舶
            "000768.SZ",  # 中航飞机
        ]
    },
    "新能源": {
        "description": "新能源汽车",
        "stocks": [
            "300750.SZ",  # 宁德时代
            "002594.SZ",  # 比亚迪
            "002475.SZ",  # 立讯精密
        ]
    },
}


def scan_hot_sectors():
    """扫描热门板块"""
    fetcher = AShareDataFetcher()
    
    print("=" * 70)
    print("🔥 热门板块扫描")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_results = {}
    
    for sector_name, sector_info in HOT_SECTORS.items():
        print(f"\n🔍 扫描: {sector_name} ({sector_info['description']})")
        
        quotes = fetcher.scan_all(sector_info['stocks'])
        
        if not quotes:
            print(f"   ⚠️ 无数据")
            continue
        
        # 计算板块指标
        changes = [q.get('change_pct', 0) for q in quotes.values()]
        avg_change = sum(changes) / len(changes) if changes else 0
        up_count = sum(1 for c in changes if c > 0)
        
        emoji = "🟢" if avg_change > 0 else "🔴"
        print(f"   {emoji} 平均涨幅: {avg_change:+.2f}% ({up_count}/{len(changes)} 上涨)")
        
        # 龙头股
        sorted_quotes = sorted(quotes.items(), key=lambda x: x[1].get('change_pct', 0), reverse=True)
        
        leaders = []
        for symbol, quote in sorted_quotes[:3]:
            if quote.get('change_pct', 0) > avg_change:
                leaders.append({
                    'symbol': symbol,
                    'name': quote.get('name', ''),
                    'change_pct': quote.get('change_pct', 0),
                    'price': quote.get('price', 0),
                })
        
        if leaders:
            print(f"   龙头:")
            for l in leaders:
                e = "🟢" if l['change_pct'] > 0 else "🔴"
                print(f"      {e} {l['name']}({l['symbol']}): {l['change_pct']:+.2f}%")
        
        all_results[sector_name] = {
            'avg_change': avg_change,
            'up_count': up_count,
            'total': len(changes),
            'leaders': leaders,
        }
    
    # 排序
    print("\n" + "=" * 70)
    print("📊 板块热度排名")
    print("=" * 70)
    
    sorted_sectors = sorted(all_results.items(), key=lambda x: x[1]['avg_change'], reverse=True)
    
    for i, (name, data) in enumerate(sorted_sectors, 1):
        emoji = "🔥" if data['avg_change'] > 1 else "🟢" if data['avg_change'] > 0 else "🔴"
        print(f"  {i}. {emoji} {name}: {data['avg_change']:+.2f}% ({data['up_count']}/{data['total']})")
    
    # 推荐板块
    print("\n" + "=" * 70)
    print("💡 板块建议")
    print("=" * 70)
    
    hot_sectors = [(name, data) for name, data in sorted_sectors if data['avg_change'] > 0]
    
    if hot_sectors:
        print("\n🔥 热门板块 (可关注):")
        for name, data in hot_sectors:
            print(f"  • {name}: {data['avg_change']:+.2f}%")
            if data['leaders']:
                for l in data['leaders'][:2]:
                    print(f"    - {l['name']}: {l['change_pct']:+.2f}%")
    else:
        print("\n⚠️ 今日无热门板块，市场整体弱势")
        print("  建议: 观望为主，等待企稳信号")
    
    return all_results


if __name__ == "__main__":
    import os
    import requests
    
    results = scan_hot_sectors()
    
    # 生成报告
    sorted_sectors = sorted(results.items(), key=lambda x: x[1]['avg_change'], reverse=True)
    
    report = f"🔥 热门板块扫描\n"
    report += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    report += "📊 板块排名:\n"
    
    for i, (name, data) in enumerate(sorted_sectors, 1):
        emoji = "🔥" if data['avg_change'] > 1 else "🟢" if data['avg_change'] > 0 else "🔴"
        report += f"  {i}. {emoji} {name}: {data['avg_change']:+.2f}%\n"
    
    hot = [(n, d) for n, d in sorted_sectors if d['avg_change'] > 0]
    if hot:
        report += f"\n🔥 热门: {', '.join([n for n, d in hot])}\n"
        for name, data in hot[:2]:
            if data['leaders']:
                report += f"  {name}龙头: {', '.join([l['name'] for l in data['leaders'][:2]])}\n"
    
    report += "\n💡 操作建议:\n"
    avg = sum(d['avg_change'] for d in results.values()) / len(results) if results else 0
    if avg < -2:
        report += "  🔴 市场弱势，观望\n"
    elif avg < 0:
        report += "  ⚠️ 震荡，轻仓\n"
    else:
        report += "  🟢 可参与\n"
    
    print("\n" + report)
    
    # 推送
    webhook = os.environ.get("FEISHU_WEBHOOK")
    if webhook:
        try:
            requests.post(webhook, json={"msg_type": "text", "content": {"text": report}}, timeout=10)
            print("\n✅ 已推送到飞书")
        except Exception as e:
            print(f"\n❌ 推送失败: {e}")
