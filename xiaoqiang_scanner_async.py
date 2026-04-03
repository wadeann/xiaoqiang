#!/usr/bin/env python3
"""
华尔街之狼 - 并发版本
使用并发数据获取，提升性能
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '.')

from data.concurrent_fetcher import ConcurrentFetcher, fetch_all_markets_sync

class WolfTraderAsync:
    def __init__(self):
        self.fetcher = ConcurrentFetcher(max_concurrent=5, rate_limit=2.0)
    
    async def scan_market_async(self):
        """并发扫描市场"""
        print("\n" + "=" * 70)
        print("🐺 华尔街之狼 - 并发扫描")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        start = datetime.now()
        
        # 并发获取所有市场数据
        results = await self.fetcher.fetch_all_markets()
        
        elapsed = (datetime.now() - start).total_seconds()
        
        # 美股
        print("\n🇺🇸 美股市场")
        print("-" * 70)
        for quote in results.get("US", []):
            emoji = "🔥" if quote["change_pct"] >= 10 else "📈" if quote["change_pct"] >= 5 else "📊"
            print(f"{emoji} {quote['symbol']}: ${quote['price']:.2f} ({quote['change_pct']:+.2f}%)")
        
        # 港股
        print("\n🇭🇰 港股市场")
        print("-" * 70)
        for quote in results.get("HK", []):
            emoji = "🔥" if quote["change_pct"] >= 10 else "📈" if quote["change_pct"] >= 5 else "📊"
            print(f"{emoji} {quote['symbol']}: ${quote['price']:.2f} ({quote['change_pct']:+.2f}%)")
        
        # A股
        print("\n🇨🇳 A股市场")
        print("-" * 70)
        for quote in results.get("A", []):
            emoji = "🔥" if quote["change_pct"] >= 5 else "📈" if quote["change_pct"] >= 3 else "📊"
            print(f"{emoji} {quote.get('name', quote['symbol'])}: ¥{quote['price']:.2f} ({quote['change_pct']:+.2f}%)")
        
        print("\n" + "=" * 70)
        print(f"✅ 扫描完成，耗时 {elapsed:.2f}秒")
        print("=" * 70 + "\n")
        
        return results
    
    def scan_market(self):
        """同步接口"""
        return asyncio.run(self.scan_market_async())

if __name__ == "__main__":
    wolf = WolfTraderAsync()
    wolf.scan_market()
