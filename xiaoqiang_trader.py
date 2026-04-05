#!/usr/bin/env python3
"""
华尔街之狼 - 自主交易引擎 (Evolution 4.0)
全自动扫描、分析、决策、执行
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path
from brain import xiaoqiang_scan_logic

# 配置
API_KEY = "rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
BASE_URL = "https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"

# 交易规则
RULES = {
    "min_change_pct": 2.0,        # 最小涨幅阈值 (进化后)
    "max_change_pct": 50.0,       # 最大涨幅阈值
    "stop_loss_pct": -10.0,       # 止损线
    "take_profit_pct": 20.0,      # 止盈线
    "position_size": 0.3,         # 单只标的仓位比例
    "max_positions": 3,           # 最大持仓数量
}

# 可交易标的
TRADEABLE = {
    "US": ["NVDA", "TSLA", "ARM", "ASML", "PLTR", "MU", "TSM", "CRWV", "IREN", "NBIS", "BABA", "BIDU"],
    "HK": ["00700.HK", "09988.HK", "09888.HK", "00981.HK", "02513.HK", "06869.HK", "00100.HK"]
}

class WolfTrader:
    def __init__(self):
        self.headers = {"X-API-Key": API_KEY}
        self.log_dir = Path("/home/wade/.openclaw/logs")
        self.log_dir.mkdir(exist_ok=True)
        
    def log(self, msg):
        """日志记录"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        
        # 写入日志文件
        log_file = self.log_dir / "xiaoqiang_trader.log"
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    
    def api_get(self, endpoint):
        """GET 请求"""
        try:
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", {}).get("data")
            else:
                self.log(f"API 错误: {data.get('message')}")
                return None
        except Exception as e:
            self.log(f"API 异常: {e}")
            return None
    
    def api_post(self, endpoint, payload):
        """POST 请求"""
        try:
            resp = requests.post(f"{BASE_URL}{endpoint}", headers=self.headers, json=payload, timeout=10)
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", {}).get("data")
            else:
                self.log(f"API 错误: {data.get('message')}")
                return None
        except Exception as e:
            self.log(f"API 异常: {e}")
            return None
    
    def get_account(self):
        """获取账户信息"""
        # 尝试不同的端点
        data = self.api_get("/positions")
        if data is not None:
            # 从持仓计算总资产
            positions = data if isinstance(data, list) else []
            total_value = sum(p.get("marketValue", 0) for p in positions)
            return {
                "total_value": total_value,
                "positions": len(positions),
            }
        return None
    
    def get_positions(self):
        """获取持仓"""
        data = self.api_get("/positions")
        return data if isinstance(data, list) else []
    
    def get_orders(self):
        """获取订单"""
        data = self.api_get("/orders")
        return data if isinstance(data, list) else []
    
    def get_quote(self, symbol, market="US"):
        """获取行情"""
        try:
            url = f"{BASE_URL}/market/tick/latest"
            params = {"symbol": symbol, "market": market}
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = resp.json()
            if data.get("code") == 200:
                quote = data.get("data", {}).get("data", {})
                return {
                    "price": quote.get("tradePrice", 0),
                    "change_pct": quote.get("changePercent", 0) * 100,  # 转为百分比
                    "volume": quote.get("volume", 0),
                    "bid": quote.get("bidPrice", 0),
                    "ask": quote.get("askPrice", 0),
                }
            else:
                return None
        except:
            return None
    
    def scan_market(self):
        """扫描市场，寻找交易机会"""
        self.log("=" * 70)
        self.log("🔍 协同扫描模式启动 (XiaoQiang + Judy + CFO)... ")
        
        opportunities = []
        
        # 扫描美股
        for symbol in TRADEABLE["US"]:
            quote = self.get_quote(symbol, "US")
            if quote and quote["price"] > 0:
                change_pct = quote["change_pct"]
                if xiaoqiang_scan_logic(symbol.lower(), quote["change_pct"] / 100.0):
                    opportunities.append({
                        "symbol": symbol,
                        "market": "US",
                        "price": quote["price"],
                        "change_pct": change_pct,
                        "volume": quote["volume"],
                    })
        
        # 扫描港股
        for symbol in TRADEABLE["HK"]:
            quote = self.get_quote(symbol, "HK")
            if quote and quote["price"] > 0:
                change_pct = quote["change_pct"]
                if xiaoqiang_scan_logic(symbol.lower(), quote["change_pct"] / 100.0):
                    opportunities.append({
                        "symbol": symbol,
                        "market": "HK",
                        "price": quote["price"],
                        "change_pct": change_pct,
                        "volume": quote["volume"],
                    })
        
        # 按涨幅排序
        opportunities.sort(key=lambda x: x["change_pct"], reverse=True)
        
        self.log(f"协同决策发现 {len(opportunities)} 个通过 AI 验证的交易机会")
        for i, opp in enumerate(opportunities[:5], 1):
            self.log(f"  {i}. {opp['symbol']}: {opp['change_pct']:+.2f}% @ ${opp['price']:.2f}")
        
        return opportunities
    
    def analyze_positions(self):
        """分析当前持仓"""
        self.log("=" * 70)
        self.log("📊 分析持仓...")
        
        positions = self.get_positions()
        
        if not positions:
            self.log("当前空仓")
            return []
        
        analysis = []
        
        for pos in positions:
            symbol = pos.get("symbol", "")
            quantity = pos.get("quantity", 0)
            avg_cost = pos.get("avgCost", 0)
            market_value = pos.get("marketValue", 0)
            pnl = pos.get("unrealizedPnl", 0)
            pnl_pct = pos.get("unrealizedPnlRate", 0) * 100 if pos.get("unrealizedPnlRate") else 0
            
            # 获取当前价格
            market = "HK" if ".HK" in symbol else "US"
            quote = self.get_quote(symbol, market)
            current_price = quote["price"] if quote else avg_cost
            current_change = quote["change_pct"] if quote else 0
            
            analysis.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "current_change": current_change,
                "market_value": market_value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "action": self._decide_action(pnl_pct),
            })
            
            self.log(f"  {symbol}: {quantity}股 | 成本 ${avg_cost:.2f} → 当前 ${current_price:.2f}")
            self.log(f"    收益: {pnl_pct:+.2f}% | 决策: {analysis[-1]['action']}")
        
        return analysis
    
    def _decide_action(self, pnl_pct):
        """决策：买入/卖出/持有"""
        if pnl_pct <= RULES["stop_loss_pct"]:
            return "SELL_STOP_LOSS"
        elif pnl_pct >= RULES["take_profit_pct"]:
            return "SELL_TAKE_PROFIT"
        else:
            return "HOLD"
    
    def execute_buy(self, symbol, market, quantity):
        """执行买入"""
        self.log(f"📈 买入 {symbol} x {quantity}")
        
        payload = {
            "symbol": symbol,
            "market": market,
            "side": "BUY",
            "orderType": "MARKET_ORDER",
            "quantity": quantity,
        }
        
        result = self.api_post("/orders", payload)
        if result:
            self.log(f"  ✅ 下单成功")
            return True
        else:
            self.log(f"  ❌ 下单失败")
            return False
    
    def execute_sell(self, symbol, market, quantity, reason=""):
        """执行卖出"""
        self.log(f"📉 卖出 {symbol} x {quantity} ({reason})")
        
        payload = {
            "symbol": symbol,
            "market": market,
            "side": "SELL",
            "orderType": "MARKET_ORDER",
            "quantity": quantity,
        }
        
        result = self.api_post("/orders", payload)
        if result:
            self.log(f"  ✅ 下单成功")
            return True
        else:
            self.log(f"  ❌ 下单失败")
            return False
    
    def run(self):
        """主循环"""
        self.log("")
        self.log("=" * 70)
        self.log("🐺 华尔街之狼 - 自主交易引擎 (Evolution 4.0)启动")
        self.log(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("=" * 70)
        
        # 1. 检查交易时段
        hour = datetime.now().hour
        is_trading = (hour >= 21 or hour < 4) or (hour >= 9 and hour < 16)
        
        if not is_trading:
            self.log("⏸️ 非交易时段，仅扫描不交易")
            self.scan_market()
            self.log("=" * 70)
            return
        
        # 2. 获取持仓信息
        position_analysis = self.analyze_positions()
        
        # 3. 执行卖出决策
        for pos in position_analysis:
            if pos["action"] == "SELL_STOP_LOSS":
                market = "HK" if ".HK" in pos["symbol"] else "US"
                self.execute_sell(pos["symbol"], market, pos["quantity"], "止损")
            elif pos["action"] == "SELL_TAKE_PROFIT":
                market = "HK" if ".HK" in pos["symbol"] else "US"
                self.execute_sell(pos["symbol"], market, pos["quantity"], "止盈")
        
        # 4. 扫描买入机会
        opportunities = self.scan_market()
        
        # 5. 执行买入决策
        current_positions = len([p for p in position_analysis if p["action"] == "HOLD"])
        available_slots = RULES["max_positions"] - current_positions
        
        if available_slots > 0 and opportunities:
            # 假设初始资金 $1,000,000
            cash = 1000000
            position_size = cash * RULES["position_size"]
            
            for opp in opportunities[:available_slots]:
                quantity = int(position_size / opp["price"])
                if quantity > 0:
                    success = self.execute_buy(opp["symbol"], opp["market"], quantity)
                    if success:
                        cash -= position_size
        
        # 6. 最终状态
        self.log("=" * 70)
        self.log("📋 交易报告")
        self.log("=" * 70)
        
        positions = self.get_positions()
        self.log(f"📈 持仓数量: {len(positions)}")
        
        self.log("=" * 70)
        self.log("✅ 华尔街之狼执行完成")
        self.log("=" * 70 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="华尔街之狼自主交易引擎 (Evolution 4.0)")
    parser.add_argument("--run", action="store_true", help="执行交易")
    parser.add_argument("--scan", action="store_true", help="仅扫描市场")
    parser.add_argument("--status", action="store_true", help="查看状态")
    
    args = parser.parse_args()
    
    wolf = WolfTrader()
    
    if args.run:
        wolf.run()
    elif args.scan:
        wolf.scan_market()
    elif args.status:
        positions = wolf.get_positions()
        orders = wolf.get_orders()
        print(f"📈 持仓数量: {len(positions)}")
        print(f"📋 订单数量: {len(orders)}")
        for pos in positions:
            print(f"  - {pos.get('symbol')}: {pos.get('quantity')}股")
    else:
        wolf.run()
