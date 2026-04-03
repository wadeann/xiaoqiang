#!/usr/bin/env python3
"""
小强量化系统 - 全市场热门股扫描器
自动发现热门板块和热门股票
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import requests
import re

sys.path.insert(0, str(Path(__file__).parent))


def get_market_overview():
    """获取大盘数据"""
    print("=" * 70)
    print("📊 全市场扫描")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取主要指数
    indices = {
        "s_sh000001": ("上证指数", "000001.SH"),
        "s_sz399001": ("深证成指", "399001.SZ"),
        "s_sz399006": ("创业板指", "399006.SZ"),
        "s_sh000688": ("科创50", "000688.SH"),
        "s_sh000300": ("沪深300", "000300.SH"),
        "s_sz399005": ("中小板指", "399005.SZ"),
    }
    
    summary = {}
    
    try:
        # 批量获取指数
        codes_str = ",".join(indices.keys())
        url = f"http://hq.sinajs.cn/list={codes_str}"
        headers = {"Referer": "http://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}
        
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "gbk"
        
        lines = resp.text.strip().split("\n")
        
        for i, (code_key, (name, symbol)) in enumerate(indices.items()):
            if i < len(lines):
                match = re.search(r'="([^"]+)"', lines[i])
                if match:
                    data = match.group(1).split(",")
                    if len(data) >= 4:
                        summary[name] = {
                            "symbol": symbol,
                            "price": float(data[1]) if data[1] else 0,
                            "change_pct": float(data[3]) if data[3] else 0,
                        }
        
        print("📈 主要指数:")
        for name, data in summary.items():
            emoji = "🟢" if data['change_pct'] > 0 else "🔴"
            print(f"  {emoji} {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)")
        
    except Exception as e:
        print(f"❌ 获取指数失败: {e}")
    
    return summary


def get_hot_sectors():
    """获取热门板块"""
    print("\n📊 扫描热门板块...")
    
    # 使用东方财富板块接口
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 50,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb0408970059f27f6f7266800",
            "fltt": 2,
            "invt": 2,
            "fid": "f3",  # 按涨幅排序
            "fs": "m:90+t:2",  # 板块
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18"
        }
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        
        if data and "data" in data and "diff" in data["data"]:
            sectors = []
            for item in data["data"]["diff"][:20]:
                name = item.get("f14", "")
                change = float(item.get("f3", 0)) / 100 if item.get("f3") else 0
                amount = float(item.get("f6", 0)) / 1e8 if item.get("f6") else 0  # 成交额(亿)
                
                if name and change:
                    sectors.append({
                        "name": name,
                        "change_pct": change,
                        "amount": amount,
                    })
            
            print("\n🔥 板块涨幅榜 Top 10:")
            for i, s in enumerate(sectors[:10], 1):
                emoji = "🔥" if s['change_pct'] > 3 else "🟢" if s['change_pct'] > 0 else "🔴"
                print(f"  {i}. {emoji} {s['name']}: {s['change_pct']:+.2f}% (成交{s['amount']:.0f}亿)")
            
            return sectors
    
    except Exception as e:
        print(f"❌ 获取板块失败: {e}")
    
    return []


def get_hot_stocks():
    """获取热门个股"""
    print("\n📊 扫描热门个股...")
    
    try:
        # 涨幅榜
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 50,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb0408970059f27f6f7266800",
            "fltt": 2,
            "invt": 2,
            "fid": "f3",  # 按涨幅排序
            "fs": "m:0+t:6,f:!2,m:1+t:2,f:!2",  # A股
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18"
        }
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        
        if data and "data" in data and "diff" in data["data"]:
            stocks = []
            for item in data["data"]["diff"][:30]:
                code = item.get("f12", "")
                name = item.get("f14", "")
                price = float(item.get("f2", 0)) / 100 if item.get("f2") else 0
                change = float(item.get("f3", 0)) / 100 if item.get("f3") else 0
                amount = float(item.get("f6", 0)) / 1e8 if item.get("f6") else 0
                turnover = float(item.get("f8", 0)) if item.get("f8") else 0  # 换手率
                
                # 过滤ST、新股
                if "ST" in name or "N" in name[:2]:
                    continue
                
                market = "SH" if code.startswith("6") else "SZ"
                symbol = f"{code}.{market}"
                
                stocks.append({
                    "symbol": symbol,
                    "name": name,
                    "price": price,
                    "change_pct": change,
                    "amount": amount,
                    "turnover": turnover,
                })
            
            print("\n🔥 个股涨幅榜 Top 15:")
            for i, s in enumerate(stocks[:15], 1):
                emoji = "🔥" if s['change_pct'] > 9.9 else "🟢"
                print(f"  {i}. {emoji} {s['name']}({s['symbol']}): {s['change_pct']:+.2f}% 成交{s['amount']:.0f}亿 换手{s['turnover']:.1f}%")
            
            return stocks
    
    except Exception as e:
        print(f"❌ 获取个股失败: {e}")
    
    return []


def generate_report(summary, sectors, stocks):
    """生成报告"""
    report = f"🔥 全市场扫描报告\n"
    report += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    # 大盘
    report += "📊 大盘走势:\n"
    for name, data in summary.items():
        emoji = "🟢" if data['change_pct'] > 0 else "🔴"
        report += f"  {emoji} {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)\n"
    
    # 板块
    if sectors:
        avg_sector = sum(s['change_pct'] for s in sectors[:10]) / len(sectors[:10])
        report += f"\n🔥 热门板块 (平均{avg_sector:+.2f}%):\n"
        hot_sectors = [s for s in sectors[:5] if s['change_pct'] > 0]
        for s in hot_sectors:
            emoji = "🔥" if s['change_pct'] > 3 else "🟢"
            report += f"  {emoji} {s['name']}: {s['change_pct']:+.2f}%\n"
    
    # 个股
    if stocks:
        report += f"\n🔥 热门个股 Top 10:\n"
        for i, s in enumerate(stocks[:10], 1):
            emoji = "🔥" if s['change_pct'] > 9.9 else "🟢"
            report += f"  {i}. {emoji} {s['name']}: {s['change_pct']:+.2f}%\n"
    
    # 建议
    report += "\n💡 操作建议:\n"
    avg = sum(s['change_pct'] for s in stocks[:20]) / len(stocks[:20]) if stocks else 0
    if avg > 2:
        report += "  🟢 市场强势，积极参与\n"
        report += "  📌 关注涨停股、龙头股\n"
    elif avg > 0:
        report += "  ⚪ 市场震荡，轻仓操作\n"
        report += "  📌 关注强势板块龙头\n"
    else:
        report += "  🔴 市场弱势，观望为主\n"
        report += "  📌 关注抗跌股，等待企稳\n"
    
    return report


def main():
    # 1. 大盘数据
    summary = get_market_overview()
    
    # 2. 热门板块
    sectors = get_hot_sectors()
    
    # 3. 热门个股
    stocks = get_hot_stocks()
    
    # 4. 生成报告
    report = generate_report(summary, sectors, stocks)
    
    print("\n" + report)
    
    # 5. 推送到飞书
    import os
    webhook = os.environ.get("FEISHU_WEBHOOK")
    if webhook:
        try:
            requests.post(
                webhook,
                json={"msg_type": "text", "content": {"text": report}},
                timeout=10
            )
            print("\n✅ 已推送到飞书")
        except Exception as e:
            print(f"\n❌ 推送失败: {e}")
    
    # 6. 保存结果
    result = {
        "time": datetime.now().isoformat(),
        "summary": summary,
        "sectors": sectors[:20],
        "stocks": stocks[:30],
    }
    
    save_file = Path(__file__).parent / "watchlist" / "market_scan.json"
    save_file.parent.mkdir(parents=True, exist_ok=True)
    with open(save_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 已保存到: {save_file}")


if __name__ == "__main__":
    main()
