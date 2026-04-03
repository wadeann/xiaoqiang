#!/usr/bin/env python3
"""
小强每日复盘系统
- 识别可买入股票
- 持续回测跟踪
- 自动剔除不符合规则的标的
- 迭代优化选股策略
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# 配置
WATCHLIST_DIR = Path("watchlist")
HISTORY_DIR = Path("history")
RULES = {
    "min_change_pct": 3.0,      # 最小涨幅阈值
    "max_change_pct": 50.0,     # 最大涨幅阈值 (防止异常)
    "min_volume": 1000000,      # 最小成交量
    "max_days_hold": 5,         # 最大持有天数
    "stop_loss_pct": -10.0,     # 止损线
    "take_profit_pct": 20.0,    # 止盈线
}

# 确保目录存在
WATCHLIST_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)

def load_watchlist():
    """加载观察列表"""
    watchlist_file = WATCHLIST_DIR / "current.json"
    if watchlist_file.exists():
        with open(watchlist_file, 'r') as f:
            return json.load(f)
    return {"stocks": [], "last_update": None}

def save_watchlist(watchlist):
    """保存观察列表"""
    watchlist["last_update"] = datetime.now().isoformat()
    watchlist_file = WATCHLIST_DIR / "current.json"
    with open(watchlist_file, 'w') as f:
        json.dump(watchlist, f, indent=2, ensure_ascii=False)

def add_to_watchlist(symbol, name, price, change_pct, reason, market="US"):
    """添加股票到观察列表"""
    watchlist = load_watchlist()
    
    # 检查是否已存在
    existing = [s for s in watchlist["stocks"] if s["symbol"] == symbol]
    if existing:
        # 更新现有记录
        existing[0].update({
            "current_price": price,
            "current_change": change_pct,
            "last_check": datetime.now().isoformat(),
        })
    else:
        # 添加新记录
        watchlist["stocks"].append({
            "symbol": symbol,
            "name": name,
            "market": market,
            "add_date": datetime.now().strftime("%Y-%m-%d"),
            "add_price": price,
            "add_change": change_pct,
            "current_price": price,
            "current_change": change_pct,
            "reason": reason,
            "days_in_list": 0,
            "highest_price": price,
            "lowest_price": price,
            "status": "watching",
            "last_check": datetime.now().isoformat(),
        })
    
    save_watchlist(watchlist)
    return not existing  # 返回是否新增

def remove_from_watchlist(symbol, reason):
    """从观察列表移除"""
    watchlist = load_watchlist()
    removed = None
    
    for i, stock in enumerate(watchlist["stocks"]):
        if stock["symbol"] == symbol:
            removed = watchlist["stocks"].pop(i)
            break
    
    if removed:
        # 保存历史记录
        history_file = HISTORY_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        history = {"removed": [], "added": []}
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        history["removed"].append({
            **removed,
            "remove_reason": reason,
            "remove_date": datetime.now().isoformat(),
        })
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        save_watchlist(watchlist)
    
    return removed

def update_watchlist_prices():
    """更新观察列表中的价格"""
    import sys
    sys.path.insert(0, '.')
    from data.realtime_fetcher import RealtimeFetcher
    from data.rockflow_config import API_KEY
    
    fetcher = RealtimeFetcher(API_KEY)
    watchlist = load_watchlist()
    
    for stock in watchlist["stocks"]:
        try:
            market = "HK" if ".HK" in stock["symbol"] else "US" if stock["market"] == "US" else "A"
            if market == "A":
                # A股使用腾讯数据源
                import akshare as ak
                df = ak.stock_zh_a_spot_em()
                code = stock["symbol"]
                row = df[df['代码'] == code.split('sh')[-1].split('sz')[-1]]
                if not row.empty:
                    current_price = float(row['最新价'].values[0])
                    change_pct = float(row['涨跌幅'].values[0])
                    stock["current_price"] = current_price
                    stock["current_change"] = change_pct
                    stock["last_check"] = datetime.now().isoformat()
            else:
                quote = fetcher.get_quote(stock["symbol"], market)
                
                if quote:
                    current_price = quote.get("price", 0)
                    change_pct = quote.get("change_pct", 0)
                    
                    stock["current_price"] = current_price
                    stock["current_change"] = change_pct
                    stock["last_check"] = datetime.now().isoformat()
                    
                    # 更新最高/最低价
                    if current_price > stock.get("highest_price", current_price):
                        stock["highest_price"] = current_price
                    if current_price < stock.get("lowest_price", current_price):
                        stock["lowest_price"] = current_price
                    
                    # 计算持有收益
                    add_price = stock.get("add_price", current_price)
                    if add_price > 0:
                        stock["holding_return"] = ((current_price - add_price) / add_price) * 100
        except Exception as e:
            print(f"更新 {stock['symbol']} 价格失败: {e}")
    
    save_watchlist(watchlist)
    return watchlist

def check_rules():
    """检查规则，剔除不符合的标的"""
    watchlist = load_watchlist()
    to_remove = []
    
    for stock in watchlist["stocks"]:
        symbol = stock["symbol"]
        current_change = stock.get("current_change", 0)
        holding_return = stock.get("holding_return", 0)
        days_in_list = stock.get("days_in_list", 0)
        
        # 规则检查
        reasons = []
        
        # 1. 涨幅低于阈值
        if current_change < RULES["min_change_pct"]:
            reasons.append(f"涨幅 {current_change:.2f}% 低于阈值 {RULES['min_change_pct']}%")
        
        # 2. 涨幅异常高
        if current_change > RULES["max_change_pct"]:
            reasons.append(f"涨幅 {current_change:.2f}% 异常，可能数据错误")
        
        # 3. 持有天数超限
        if days_in_list >= RULES["max_days_hold"]:
            reasons.append(f"持有 {days_in_list} 天，超过最大天数 {RULES['max_days_hold']}")
        
        # 4. 触发止损
        if holding_return < RULES["stop_loss_pct"]:
            reasons.append(f"持有收益 {holding_return:.2f}% 触发止损")
        
        # 5. 触发止盈
        if holding_return > RULES["take_profit_pct"]:
            reasons.append(f"持有收益 {holding_return:.2f}% 触发止盈")
        
        if reasons:
            to_remove.append((symbol, "; ".join(reasons)))
    
    # 执行移除
    removed_stocks = []
    for symbol, reason in to_remove:
        removed = remove_from_watchlist(symbol, reason)
        if removed:
            removed_stocks.append((symbol, reason))
    
    return removed_stocks

def scan_and_add():
    """扫描市场，添加符合规则的标的"""
    import sys
    sys.path.insert(0, '.')
    from data.realtime_fetcher import RealtimeFetcher
    from data.rockflow_config import API_KEY
    
    fetcher = RealtimeFetcher(API_KEY)
    
    added = []
    
    # 扫描美股/港股
    us_symbols = ["NBIS", "CRWV", "ARM", "NVDA", "TSLA", "PLTR", "MU", "TSM", "IREN", 
                  "00100.HK", "00700.HK", "00981.HK", "02513.HK", "06869.HK", "09888.HK", "09988.HK"]
    
    for symbol in us_symbols:
        try:
            market = "HK" if ".HK" in symbol else "US"
            quote = fetcher.get_quote(symbol, market)
            
            if quote:
                price = quote.get("price", 0)
                change_pct = quote.get("change_pct", 0)
                
                if change_pct >= RULES["min_change_pct"] and change_pct <= RULES["max_change_pct"]:
                    is_new = add_to_watchlist(
                        symbol=symbol,
                        name=symbol,
                        price=price,
                        change_pct=change_pct,
                        reason=f"涨幅 {change_pct:.2f}% 超过阈值",
                        market=market
                    )
                    if is_new:
                        added.append((symbol, change_pct))
        except Exception as e:
            pass
    
    # 扫描A股 AI板块 (使用akshare)
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        
        # AI/半导体板块股票代码
        ai_codes = {
            "603259": "药明康德",
            "300661": "圣邦股份",
            "688981": "中芯国际",
            "688012": "中微公司",
            "002475": "立讯精密",
            "300124": "汇川技术",
            "300059": "东方财富",
            "300750": "宁德时代",
            "002415": "海康威视",
        }
        
        for code, name in ai_codes.items():
            row = df[df['代码'] == code]
            if not row.empty:
                try:
                    price = float(row['最新价'].values[0])
                    change_pct = float(row['涨跌幅'].values[0])
                    
                    if change_pct >= RULES["min_change_pct"]:
                        is_new = add_to_watchlist(
                            symbol=f"sh{code}" if code.startswith('6') else f"sz{code}",
                            name=name,
                            price=price,
                            change_pct=change_pct,
                            reason=f"涨幅 {change_pct:.2f}% 超过阈值",
                            market="A"
                        )
                        if is_new:
                            added.append((name, change_pct))
                except:
                    pass
    except Exception as e:
        print(f"A股数据获取失败: {e}")
    
    return added

def generate_report():
    """生成复盘报告"""
    watchlist = load_watchlist()
    
    print("\n" + "="*70)
    print("📊 小强每日复盘报告")
    print(f"📅 日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    # 当前观察列表
    print("\n📋 当前观察列表")
    print("-"*70)
    if not watchlist["stocks"]:
        print("暂无观察标的")
    else:
        for stock in watchlist["stocks"]:
            symbol = stock["symbol"]
            name = stock.get("name", symbol)
            add_price = stock.get("add_price", 0)
            current_price = stock.get("current_price", 0)
            current_change = stock.get("current_change", 0)
            holding_return = stock.get("holding_return", 0)
            days = stock.get("days_in_list", 0)
            status = stock.get("status", "watching")
            
            emoji = "🔥" if current_change >= 5 else "📈" if current_change >= 3 else "📊"
            return_emoji = "🟢" if holding_return >= 0 else "🔴"
            
            print(f"{emoji} {name} ({symbol})")
            print(f"   加入: ${add_price:.2f} | 当前: ${current_price:.2f} | 收益: {return_emoji} {holding_return:+.2f}%")
            print(f"   当日涨幅: {current_change:+.2f}% | 观察天数: {days} | 状态: {status}")
            print()
    
    # 统计
    total = len(watchlist["stocks"])
    profit = sum(1 for s in watchlist["stocks"] if s.get("holding_return", 0) > 0)
    loss = total - profit
    
    print("-"*70)
    print(f"📊 统计: 共 {total} 只 | 盈利 {profit} 只 | 亏损 {loss} 只")
    
    # 规则说明
    print("\n📌 选股规则")
    print("-"*70)
    for rule, value in RULES.items():
        print(f"• {rule}: {value}")
    
    print("\n" + "="*70)
    print("✅ 复盘完成")
    print("="*70 + "\n")
    
    return watchlist

def increment_days():
    """增加观察天数"""
    watchlist = load_watchlist()
    for stock in watchlist["stocks"]:
        stock["days_in_list"] = stock.get("days_in_list", 0) + 1
    save_watchlist(watchlist)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="小强每日复盘系统")
    parser.add_argument("--scan", action="store_true", help="扫描并添加新标的")
    parser.add_argument("--check", action="store_true", help="检查规则，剔除不合格标的")
    parser.add_argument("--update", action="store_true", help="更新价格")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--new-day", action="store_true", help="新的一天，增加观察天数")
    parser.add_argument("--all", action="store_true", help="执行所有步骤")
    
    args = parser.parse_args()
    
    if args.all:
        print("🔄 执行完整复盘流程...")
        print()
        
        # 1. 增加观察天数
        print("📅 增加观察天数...")
        increment_days()
        
        # 2. 更新价格
        print("💰 更新价格...")
        update_watchlist_prices()
        
        # 3. 检查规则
        print("🔍 检查规则...")
        removed = check_rules()
        if removed:
            print("\n剔除标的:")
            for symbol, reason in removed:
                print(f"  ❌ {symbol}: {reason}")
        
        # 4. 扫描新标的
        print("\n🔎 扫描新标的...")
        added = scan_and_add()
        if added:
            print("\n新增标的:")
            for symbol, change in added:
                print(f"  ✅ {symbol}: +{change:.2f}%")
        
        # 5. 生成报告
        print()
        generate_report()
    
    elif args.new_day:
        increment_days()
        print("✅ 观察天数已增加")
    
    elif args.update:
        update_watchlist_prices()
        print("✅ 价格已更新")
    
    elif args.check:
        removed = check_rules()
        if removed:
            print("剔除标的:")
            for symbol, reason in removed:
                print(f"  ❌ {symbol}: {reason}")
        else:
            print("✅ 无需剔除")
    
    elif args.scan:
        added = scan_and_add()
        if added:
            print("新增标的:")
            for symbol, change in added:
                print(f"  ✅ {symbol}: +{change:.2f}%")
        else:
            print("无新增标的")
    
    elif args.report:
        generate_report()
    
    else:
        generate_report()

if __name__ == "__main__":
    main()
