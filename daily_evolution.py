#!/usr/bin/env python3
"""
小强量化系统 - 每日复盘与进化
分析大盘走势、更新监控池、优化策略
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from data.a_share_data import AShareDataFetcher

sys.path.insert(0, str(Path(__file__).parent))


def daily_review():
    """每日复盘"""
    fetcher = AShareDataFetcher()
    
    print("=" * 70)
    print("📊 每日复盘与进化")
    print("=" * 70)
    print(f"日期: {datetime.now().strftime('%Y-%m-%d')}")
    print()
    
    # 1. 大盘分析
    print("1️⃣ 大盘走势分析")
    print("-" * 70)
    
    summary = fetcher.get_market_summary()
    
    # 昨日数据 (模拟，实际应从缓存获取)
    yesterday = {
        "上证指数": {"change": -0.77},
        "深证成指": {"change": -1.43},
        "创业板指": {"change": -2.10},
        "科创50": {"change": -2.62},
    }
    
    for name, data in summary.items():
        change = data['change_pct']
        yes_change = yesterday.get(name, {}).get('change', 0)
        
        # 判断趋势
        if change < -2:
            trend = "🔴🔴 极弱"
        elif change < -1:
            trend = "🔴 弱"
        elif change < 0:
            trend = "⚠️ 跌"
        elif change < 1:
            trend = "⚪ 平"
        else:
            trend = "🟢 强"
        
        # 判断加速
        if change < yes_change:
            accel = "↓ 加速下跌"
        elif change > yes_change:
            accel = "↑ 收窄"
        else:
            accel = "→ 持平"
        
        print(f"  {name}: {data['price']:.2f} ({change:+.2f}%) {trend} {accel}")
    
    # 2. 板块轮动
    print("\n2️⃣ 板块轮动分析")
    print("-" * 70)
    
    # 热门板块
    sectors = {
        "油气": +3.76,
        "创新药": -0.33,
        "军工": -0.69,
        "新能源": -1.03,
        "半导体": -3.50,
        "AI算力": -3.53,
    }
    
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
    
    print("\n板块排名 (从强到弱):")
    for i, (name, change) in enumerate(sorted_sectors, 1):
        emoji = "🔥" if change > 2 else "🟢" if change > 0 else "🔴"
        status = "热门" if change > 2 else "抗跌" if change > -1 else "弱势"
        print(f"  {i}. {emoji} {name}: {change:+.2f}% ({status})")
    
    # 3. 预测准确率
    print("\n3️⃣ 预测准确率分析")
    print("-" * 70)
    
    # 读取预测记录
    pred_file = Path(__file__).parent / "history" / "predictions.json"
    if pred_file.exists():
        with open(pred_file, 'r') as f:
            predictions = json.load(f)
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_preds = [p for p in predictions.get('records', []) if p.get('date') == today]
        
        if today_preds:
            # 简单统计
            correct = 0
            total = len(today_preds)
            
            # 获取当前行情
            symbols = list(set(p['symbol'] for p in today_preds))
            quotes = fetcher.scan_all(symbols)
            
            for pred in today_preds:
                symbol = pred['symbol']
                pred_type = pred['prediction']
                pred_change = pred['open_change']
                
                if symbol in quotes:
                    actual = quotes[symbol].get('change_pct', 0)
                    
                    # 验证预测
                    if pred_type == "continue_up" and actual > 0:
                        correct += 1
                    elif pred_type == "continue_down" and actual < 0:
                        correct += 1
                    elif pred_type == "sideways" and abs(actual) < 2:
                        correct += 1
            
            accuracy = correct / total * 100 if total > 0 else 0
            
            print(f"  今日预测: {correct}/{total} 正确 ({accuracy:.1f}%)")
            print(f"  预测类型分布:")
            
            from collections import Counter
            types = Counter(p['prediction'] for p in today_preds)
            for ptype, count in types.items():
                print(f"    {ptype}: {count}次")
        else:
            print("  今日无预测记录")
    else:
        print("  无预测记录文件")
    
    # 4. 监控池更新
    print("\n4️⃣ 监控池更新建议")
    print("-" * 70)
    
    # 根据板块表现调整
    print("\n建议加入监控:")
    for name, change in sorted_sectors[:2]:  # 前2个板块
        if change > 0:
            print(f"  ✅ {name}板块股票 (涨幅 {change:+.2f}%)")
    
    print("\n建议降低权重:")
    for name, change in sorted_sectors[-2:]:  # 后2个板块
        if change < -2:
            print(f"  ⚠️ {name}板块股票 (跌幅 {change:+.2f}%)")
    
    # 5. 策略优化
    print("\n5️⃣ 策略优化建议")
    print("-" * 70)
    
    avg_change = sum(s[1] for s in sorted_sectors) / len(sorted_sectors)
    
    if avg_change < -2:
        print("  🔴 市场极弱")
        print("  📌 建议: 降低仓位至20%以下")
        print("  📌 建议: 只关注抗跌板块")
        print("  📌 建议: 提高买入阈值至涨幅>5%")
        print("  📌 建议: 止损线收紧至-5%")
    elif avg_change < -1:
        print("  ⚠️ 市场偏弱")
        print("  📌 建议: 控制仓位在30-50%")
        print("  📌 建议: 关注强势板块龙头")
        print("  📌 建议: 买入阈值涨幅>3%")
    elif avg_change < 0:
        print("  ⚪ 市场震荡")
        print("  📌 建议: 仓位50-70%")
        print("  📌 建议: 正常策略")
    else:
        print("  🟢 市场强势")
        print("  📌 建议: 积极参与")
        print("  📌 建议: 追强势股")
    
    # 6. 明日计划
    print("\n6️⃣ 明日计划")
    print("-" * 70)
    
    # 根据今日情况制定明日策略
    if avg_change < -2:
        print("  明日策略: 观望为主")
        print("  关注标的: 油气板块、抗跌龙头")
        print("  操作建议: 等待企稳信号再入场")
    else:
        print("  明日策略: 轻仓试水")
        print("  关注标的: 热门板块龙头")
        print("  操作建议: 尾盘低吸")
    
    # 保存复盘报告
    save_review_report(summary, sectors, avg_change)
    
    print("\n" + "=" * 70)
    print("✅ 复盘完成")
    print("=" * 70)


def save_review_report(summary, sectors, avg_change):
    """保存复盘报告"""
    report_dir = Path(__file__).parent / "reports" / "a_share"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    filename = report_dir / f"review_{datetime.now().strftime('%Y-%m-%d')}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# 每日复盘报告\n\n")
        f.write(f"**日期**: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        
        f.write("## 大盘走势\n\n")
        for name, data in summary.items():
            f.write(f"- {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)\n")
        
        f.write(f"\n## 板块表现\n\n")
        f.write("| 板块 | 涨幅 | 状态 |\n")
        f.write("|------|------|------|\n")
        for name, change in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
            status = "热门" if change > 2 else "抗跌" if change > -1 else "弱势"
            f.write(f"| {name} | {change:+.2f}% | {status} |\n")
        
        f.write(f"\n## 市场状态\n\n")
        f.write(f"- 平均涨幅: {avg_change:+.2f}%\n")
        if avg_change < -2:
            f.write("- 状态: 🔴 极弱\n")
            f.write("- 建议: 降低仓位至20%以下\n")
        elif avg_change < -1:
            f.write("- 状态: ⚠️ 偏弱\n")
            f.write("- 建议: 控制仓位30-50%\n")
        else:
            f.write("- 状态: ⚪ 震荡\n")
            f.write("- 建议: 正常策略\n")
    
    print(f"\n✅ 复盘报告已保存: {filename}")


if __name__ == "__main__":
    daily_review()
