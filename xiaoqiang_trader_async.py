#!/usr/bin/env python3
"""
华尔街之狼 - 并发版本 (优化)
- 并发获取数据
- 多数据源备份
- 智能限流
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '.')

from data.concurrent_fetcher import ConcurrentFetcher

# 配置
API_KEY = "rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
BASE_URL = "https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"

# 交易规则
RULES = {
    "min_change_pct": 4.0,
    "max_change_pct": 50.0,
    "stop_loss_pct": -10.0,
    "take_profit_pct": 20.0,
    "position_size": 0.3,
    "max_positions": 3,
}

# 可交易标的
TRADEABLE = {
    "US": ["NVDA", "TSLA", "ARM", "ASML", "PLTR", "MU", "TSM", "CRWV", "IREN", "NBIS", "BABA", "BIDU"],
    "HK": ["00700.HK", "09988.HK", "09888.HK", "00981.HK", "02513.HK", "06869.HK", "00100.HK"],
    "A": ["sh603259", "sz300661", "sh688981", "sh688012"],  # A股观察
}

class WolfTraderAsync:
    def __init__(self):
        self.fetcher = ConcurrentFetcher(max_concurrent=5, rate_limit=2.0)
        self.headers = {"X-API-Key": API_KEY}
        self.log_dir = Path("/home/wade/.openclaw/logs")
        self.log_dir.mkdir(exist_ok=True)
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        log_file = self.log_dir / "xiaoqiang_trader.log"
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    
    async def scan_market_async(self):
        """并发扫描市场"""
        import asyncio
        
        self.log("=" * 70)
        self.log("🔍 并发扫描市场...")
        
        start = datetime.now()
        
        # 并发获取所有数据
        results = await self.fetcher.fetch_all_markets()
        
        elapsed = (datetime.now() - start).total_seconds()
        
        # 整理结果
        opportunities = []
        
        for market, quotes in results.items():
            for quote in quotes:
                change_pct = quote.get("change_pct", 0)
                if RULES["min_change_pct"] <= change_pct <= RULES["max_change_pct"]:
                    opportunities.append({
                        "symbol": quote["symbol"],
                        "market": market,
                        "price": quote["price"],
                        "change_pct": change_pct,
                        "source": quote.get("source", "unknown"),
                    })
        
        # 按涨幅排序
        opportunities.sort(key=lambda x: x["change_pct"], reverse=True)
        
        self.log(f"发现 {len(opportunities)} 个交易机会 (耗时 {elapsed:.2f}秒)")
        
        for i, opp in enumerate(opportunities[:10], 1):
            emoji = "🔥🔥🔥" if opp["change_pct"] >= 20 else "🔥🔥" if opp["change_pct"] >= 10 else "🔥"
            self.log(f"  {i}. {emoji} {opp['symbol']}: {opp['change_pct']:+.2f}% @ ${opp['price']:.2f} [{opp['source']}]")
        
        return opportunities
    
    def scan_market(self):
        """同步接口"""
        import asyncio
        return asyncio.run(self.scan_market_async())

if __name__ == "__main__":
    import asyncio
    wolf = WolfTraderAsync()
    wolf.scan_market()
