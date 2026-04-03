#!/usr/bin/env python3
"""
小强量化系统 - 推送报告到飞书
通过 Feishu Webhook 发送报告
"""

import sys
import json
import requests
from pathlib import Path
from datetime import datetime
import os

sys.path.insert(0, str(Path(__file__).parent))

from data.a_share_data import AShareDataFetcher
from data.rockflow_config import US_TICKERS, HK_TICKERS, A_SHARE_TICKERS
from data.realtime_fetcher import RealtimeFetcher
from data.rockflow_adapter import RockflowAdapter
from data.rockflow_config import API_KEY, BASE_URL

# Feishu Webhook
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "https://open.feishu.cn/open-apis/bot/v2/hook/c4117646-3e33-4023-a248-d91baa0d921d")


def send_to_feishu(content: str, title: str = "小强量化报告"):
    """发送消息到飞书"""
    payload = {
        "msg_type": "text",
        "content": {
            "text": content
        }
    }
    
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        result = resp.json()
        if result.get("StatusCode") == 0 or result.get("code") == 0:
            print(f"✅ 消息已发送到飞书")
            return True
        else:
            print(f"❌ 发送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        return False


def generate_a_share_report():
    """生成 A股报告"""
    fetcher = AShareDataFetcher()
    
    summary = fetcher.get_market_summary()
    quotes = fetcher.scan_all()
    
    quote_list = []
    for symbol, q in quotes.items():
        quote_list.append({
            'symbol': symbol,
            'name': q.get('name', ''),
            'price': q.get('price', 0),
            'change_pct': q.get('change_pct', 0),
            'turnover': q.get('turnover', 0),
            'volume': q.get('volume', 0),
            'amount': q.get('amount', 0)
        })
    
    sorted_quotes = sorted(quote_list, key=lambda x: x['change_pct'], reverse=True)
    
    # 龙头股
    leaders = []
    for q in quote_list:
        score = 0
        change = q.get('change_pct', 0)
        turnover = q.get('turnover', 0)
        amount = q.get('amount', 0) or q.get('volume', 0)
        
        if change > 3: score += 30
        elif change > 1: score += 20
        elif change > 0: score += 10
        
        if amount > 100000000: score += 30
        elif amount > 50000000: score += 20
        elif amount > 10000000: score += 10
        
        if turnover > 5: score += 20
        elif turnover > 3: score += 10
        
        if score >= 40:
            leaders.append({'symbol': q['symbol'], 'name': q.get('name', ''), 'price': q.get('price', 0), 'change_pct': change, 'score': score})
    
    leaders.sort(key=lambda x: x['score'], reverse=True)
    
    # 机会
    avg_change = sum(q['change_pct'] for q in quote_list) / len(quote_list) if quote_list else 0
    opportunities = []
    for q in quote_list:
        change = q.get('change_pct', 0)
        turnover = q.get('turnover', 0)
        
        if change > 3 and turnover > 3:
            opportunities.append({'type': '🟢强势突破', 'symbol': q['symbol'], 'name': q.get('name', ''), 'change_pct': change})
        elif change < -5 and turnover > 1:
            opportunities.append({'type': '🔄超跌反弹', 'symbol': q['symbol'], 'name': q.get('name', ''), 'change_pct': change})
        elif change > -1 and turnover > 2 and avg_change < -1 and change > avg_change + 1:
            opportunities.append({'type': '💪抗跌龙头', 'symbol': q['symbol'], 'name': q.get('name', ''), 'change_pct': change})
    
    # 风险
    risks = [q for q in quote_list if q['change_pct'] < -3]
    risks.sort(key=lambda x: x['change_pct'])
    
    # 构建报告
    report = f"🐉 小强A股扫描报告\n"
    report += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    report += "📊 市场概况:\n"
    for name, data in summary.items():
        emoji = "🟢" if data['change_pct'] > 0 else "🔴"
        report += f"  {emoji} {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)\n"
    
    report += "\n🐉 龙头股:\n"
    if leaders:
        for i, l in enumerate(leaders[:3], 1):
            report += f"  {i}. {l['name']}({l['symbol']}): ¥{l['price']:.2f} ({l['change_pct']:+.2f}%)\n"
    else:
        report += "  今日无明显龙头股\n"
    
    report += "\n💰 买入机会:\n"
    if opportunities:
        for i, opp in enumerate(opportunities[:3], 1):
            report += f"  {i}. {opp['type']} {opp['name']}: {opp['change_pct']:+.2f}%\n"
    else:
        report += "  今日无明显买入机会\n"
    
    report += "\n⚠️ 风险提示:\n"
    if risks:
        for i, r in enumerate(risks[:3], 1):
            report += f"  {i}. {r['name']}({r['symbol']}): {r['change_pct']:+.2f}%\n"
    else:
        report += "  暂无明显风险股\n"
    
    up_count = sum(1 for q in quote_list if q['change_pct'] > 0)
    report += f"\n💡 操作建议:\n"
    if avg_change < -2:
        report += "  🔴 市场弱势，控制仓位\n"
    elif avg_change < 0:
        report += "  ⚠️ 市场震荡，轻仓操作\n"
    else:
        report += "  🟢 市场强势，可适当参与\n"
    
    report += f"  上涨/下跌: {up_count}/{len(quote_list) - up_count}\n"
    report += f"  平均涨幅: {avg_change:+.2f}%\n"
    
    return report


def generate_us_share_report():
    """生成美股报告"""
    adapter = RockflowAdapter(API_KEY, BASE_URL)
    fetcher = RealtimeFetcher(API_KEY)
    
    assets = adapter.get_assets()
    positions = adapter.get_positions()
    quotes = fetcher.scan_all()
    
    sorted_quotes = sorted(quotes.items(), key=lambda x: x[1].get('change_pct', 0), reverse=True)
    
    report = f"🐉 小强美股报告\n"
    report += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    if assets:
        total = assets.get('total', 0)
        cash = assets.get('cash', 0)
        pnl = total - 1000000
        pnl_pct = (pnl / 1000000) * 100
        
        report += f"💰 账户状态:\n"
        report += f"  总资产: ${total:,.2f}\n"
        report += f"  现金: ${cash:,.2f}\n"
        report += f"  收益: ${pnl:,.2f} ({pnl_pct:+.2f}%)\n"
    
    if positions:
        total_value = 0
        total_profit = 0
        report += f"\n📈 持仓:\n"
        for pos in positions:
            symbol = pos.get('symbol', '')
            qty = pos.get('quantity', 0)
            market_value = pos.get('marketValue', 0)
            profit_pct = pos.get('profitPercent', 0)
            total_value += market_value
            total_profit += pos.get('profit', 0)
            status = "✅" if profit_pct >= 0 else "❄️"
            report += f"  {status} {symbol}: {int(qty)}股 | ${market_value:,.0f} | {profit_pct*100:+.2f}%\n"
        
        report += f"\n💰 总市值: ${total_value:,.0f}\n"
        report += f"📊 总盈亏: ${total_profit:+,.0f} ({total_profit/total_value*100:+.2f}%)\n"
    
    report += f"\n🔥 美股涨幅 Top 5:\n"
    for i, (symbol, quote) in enumerate(sorted_quotes[:5], 1):
        change = quote.get('change_pct', 0)
        price = quote.get('price', 0)
        emoji = "🟢" if change > 0 else "🔴"
        report += f"  {i}. {emoji} {symbol}: ${price:.2f} ({change:+.2f}%)\n"
    
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="推送报告到飞书")
    parser.add_argument("--mode", choices=["a_share", "us_share"], default="a_share", help="市场模式")
    parser.add_argument("--dry-run", action="store_true", help="只打印不发送")
    
    args = parser.parse_args()
    
    if args.mode == "a_share":
        report = generate_a_share_report()
    else:
        report = generate_us_share_report()
    
    print(report)
    print("\n" + "="*50)
    
    if args.dry_run:
        print("[DRY-RUN] 不发送消息")
    else:
        send_to_feishu(report)
