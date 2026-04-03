#!/usr/bin/env python3
"""
小强量化系统 - 自动风控监控
每小时扫描市场并决策
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

API_KEY = "rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
BASE_URL = "https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"

LOG_DIR = Path("/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang-logs")
LOG_DIR.mkdir(exist_ok=True)

# 风控参数
STARTING_CAPITAL = 1000000
STOP_LOSS_PCT = -0.10          # 止损 -10%
TAKE_PROFIT_PCT = 0.20         # 止盈 +20%
TRAILING_STOP_PCT = 0.08       # 移动止损 8%
TIER1_PROFIT_PCT = 0.15        # 分级止盈1: +15%
TIER2_PROFIT_PCT = 0.25        # 分级止盈2: +25%
TIER3_PROFIT_PCT = 0.35        # 分级止盈3: +35%

# 状态记录
high_water_mark = STARTING_CAPITAL
tier1_executed = False
tier2_executed = False

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    print(line)
    log_file = LOG_DIR / f"risk_control_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a") as f:
        f.write(line + "\n")

def api_get(endpoint):
    r = requests.get(f"{BASE_URL}{endpoint}", headers={"X-API-Key": API_KEY}, timeout=10)
    return r.json()

def api_post(endpoint, data):
    r = requests.post(f"{BASE_URL}{endpoint}", headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }, json=data, timeout=10)
    return r.json()

def get_account():
    data = api_get("/assets")
    if "data" in data and "data" in data["data"]:
        acc = data["data"]["data"]["broker"]["account"][0]
        return {
            "total": acc.get("totalAssets", 0),
            "cash": acc.get("availableCash", {}).get("USD", 0),
            "buying_power": acc.get("buyingPower", 0)
        }
    return None

def get_positions():
    data = api_get("/positions")
    if "data" in data and "data" in data["data"]:
        return data["data"]["data"]
    return []

def get_quote(symbol, market="US"):
    data = api_get(f"/market/tick/latest?market={market}&symbol={symbol}")
    if "data" in data and "data" in data["data"]:
        d = data["data"]["data"]
        return {
            "price": d.get("tradePrice") or d.get("close", 0),
            "change_pct": d.get("changePercent", 0)
        }
    return None

def sell_stock(symbol, market, qty):
    order_data = {
        "market": market,
        "symbol": symbol,
        "instrument": "STOCK",
        "orderType": "MARKET_ORDER",
        "quantity": qty,
        "side": "SELL",
        "validity": "GOOD_FOR_DAY",
        "session": "TRADING_SESSION"
    }
    return api_post("/orders", order_data)

def risk_control_check():
    global high_water_mark, tier1_executed, tier2_executed
    
    log("=" * 60)
    log("🐉 小强风控检查")
    log("=" * 60)
    
    # 获取账户
    account = get_account()
    if not account:
        log("无法获取账户信息", "ERROR")
        return
    
    total = account["total"]
    pnl = total - STARTING_CAPITAL
    pnl_pct = pnl / STARTING_CAPITAL
    
    # 更新最高点
    if total > high_water_mark:
        high_water_mark = total
        log(f"新高点: ${high_water_mark:,.2f}")
    
    # 移动止损检查
    drawdown = (high_water_mark - total) / high_water_mark if high_water_mark > 0 else 0
    
    log(f"总资产: ${total:,.2f} | 收益: ${pnl:+,.2f} ({pnl_pct:+.2%})")
    log(f"最高点: ${high_water_mark:,.2f} | 回撤: {drawdown:.2%}")
    
    # 获取持仓
    positions = get_positions()
    log(f"持仓数量: {len(positions)}")
    
    # 风控决策
    action = "HOLD"
    reason = ""
    
    # 1. 硬止损
    if pnl_pct <= STOP_LOSS_PCT:
        action = "SELL_ALL"
        reason = f"触发硬止损: {pnl_pct:.2%} <= {STOP_LOSS_PCT:.2%}"
    
    # 2. 移动止损
    elif drawdown >= TRAILING_STOP_PCT:
        action = "SELL_ALL"
        reason = f"触发移动止损: 回撤 {drawdown:.2%} >= {TRAILING_STOP_PCT:.2%}"
    
    # 3. 分级止盈
    elif pnl_pct >= TIER3_PROFIT_PCT and not tier2_executed:
        action = "SELL_ALL"
        reason = f"触发止盈3: {pnl_pct:.2%} >= {TIER3_PROFIT_PCT:.2%}"
    
    elif pnl_pct >= TIER2_PROFIT_PCT and not tier2_executed:
        action = "SELL_HALF"
        reason = f"触发止盈2: {pnl_pct:.2%} >= {TIER2_PROFIT_PCT:.2%}"
        tier2_executed = True
    
    elif pnl_pct >= TIER1_PROFIT_PCT and not tier1_executed:
        action = "SELL_ONE_THIRD"
        reason = f"触发止盈1: {pnl_pct:.2%} >= {TIER1_PROFIT_PCT:.2%}"
        tier1_executed = True
    
    # 4. 达到止盈目标
    elif pnl_pct >= TAKE_PROFIT_PCT:
        action = "SELL_ALL"
        reason = f"达到止盈目标: {pnl_pct:.2%} >= {TAKE_PROFIT_PCT:.2%}"
    
    # 执行动作
    if action == "SELL_ALL":
        log(f"⚠️ {reason}", "RISK")
        log("执行清仓...")
        for pos in positions:
            symbol = pos.get("symbol")
            qty = pos.get("quantity", 0)
            market = "HK" if ".HK" in symbol else "US"
            log(f"卖出 {symbol}: {qty}股")
            result = sell_stock(symbol, market, int(qty))
            log(f"结果: {result}")
            time.sleep(0.5)
    
    elif action == "SELL_HALF":
        log(f"📈 {reason}", "PROFIT")
        log("卖出 1/2 仓位...")
        for pos in positions:
            symbol = pos.get("symbol")
            qty = pos.get("quantity", 0)
            market = "HK" if ".HK" in symbol else "US"
            sell_qty = int(qty * 0.5)
            if sell_qty > 0:
                log(f"卖出 {symbol}: {sell_qty}股")
                result = sell_stock(symbol, market, sell_qty)
                log(f"结果: {result}")
                time.sleep(0.5)
    
    elif action == "SELL_ONE_THIRD":
        log(f"📈 {reason}", "PROFIT")
        log("卖出 1/3 仓位...")
        for pos in positions:
            symbol = pos.get("symbol")
            qty = pos.get("quantity", 0)
            market = "HK" if ".HK" in symbol else "US"
            sell_qty = int(qty / 3)
            if sell_qty > 0:
                log(f"卖出 {symbol}: {sell_qty}股")
                result = sell_stock(symbol, market, sell_qty)
                log(f"结果: {result}")
                time.sleep(0.5)
    
    else:
        log(f"✅ 安全区，继续持有")
        
        # 显示持仓状态
        for pos in positions:
            symbol = pos.get("symbol")
            qty = pos.get("quantity", 0)
            market = "HK" if ".HK" in symbol else "US"
            quote = get_quote(symbol, market)
            if quote:
                log(f"  {symbol}: {qty}股 @ ${quote['price']:.2f} ({quote['change_pct']:+.2f}%)")
            time.sleep(0.2)
    
    log("=" * 60)
    return action

def main():
    log("🚀 小强风控系统启动")
    log(f"止损: {STOP_LOSS_PCT:.0%} | 止盈: {TAKE_PROFIT_PCT:.0%} | 移动止损: {TRAILING_STOP_PCT:.0%}")
    log(f"分级止盈: {TIER1_PROFIT_PCT:.0%}卖1/3, {TIER2_PROFIT_PCT:.0%}卖1/2, {TIER3_PROFIT_PCT:.0%}清仓")
    
    # 单次检查
    risk_control_check()

if __name__ == "__main__":
    main()