#!/usr/bin/env python3
"""
并发数据获取器
- 多数据源备份
- 并发请求
- 智能限流
- 错误重试
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import random

class ConcurrentFetcher:
    def __init__(self, max_concurrent: int = 5, rate_limit: float = 0.5):
        """
        初始化并发获取器
        
        Args:
            max_concurrent: 最大并发数
            rate_limit: 每秒请求数限制
        """
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.last_request_time = {}
        self.session = None
        
        # 数据源配置
        self.data_sources = {
            "rockflow": {
                "url": "https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1",
                "api_key": "rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI",
                "priority": 1,  # 主数据源
                "markets": ["US", "HK"],
            },
            "sina": {
                "url": "https://hq.sinajs.cn/list=",
                "priority": 2,  # 备用数据源 (A股)
                "markets": ["A"],
            },
            "tencent": {
                "url": "https://web.sqt.gtimg.cn/q=",
                "priority": 3,  # 备用数据源 (A股)
                "markets": ["A"],
            },
        }
        
        # 符号映射
        self.symbol_mapping = {
            # 美股 -> Rockflow
            "US": {
                "NVDA": ("NVDA", "rockflow"),
                "TSLA": ("TSLA", "rockflow"),
                "ARM": ("ARM", "rockflow"),
                "ASML": ("ASML", "rockflow"),
                "PLTR": ("PLTR", "rockflow"),
                "MU": ("MU", "rockflow"),
                "TSM": ("TSM", "rockflow"),
                "CRWV": ("CRWV", "rockflow"),
                "IREN": ("IREN", "rockflow"),
                "NBIS": ("NBIS", "rockflow"),
                "BABA": ("BABA", "rockflow"),
                "BIDU": ("BIDU", "rockflow"),
            },
            # 港股 -> Rockflow
            "HK": {
                "00700.HK": ("00700.HK", "rockflow"),
                "09988.HK": ("09988.HK", "rockflow"),
                "09888.HK": ("09888.HK", "rockflow"),
                "00981.HK": ("00981.HK", "rockflow"),
                "02513.HK": ("02513.HK", "rockflow"),
                "06869.HK": ("06869.HK", "rockflow"),
                "00100.HK": ("00100.HK", "rockflow"),
            },
            # A股 -> 新浪/腾讯
            "A": {
                "sh603259": ("sh603259", "sina"),  # 药明康德
                "sz300661": ("sz300661", "sina"),  # 圣邦股份
                "sh688981": ("sh688981", "tencent"),  # 中芯国际
                "sh688012": ("sh688012", "tencent"),  # 中微公司
            },
        }
    
    async def _rate_limit_wait(self, source: str):
        """限流等待"""
        if source not in self.last_request_time:
            self.last_request_time[source] = 0
        
        elapsed = time.time() - self.last_request_time[source]
        wait_time = (1.0 / self.rate_limit) - elapsed
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self.last_request_time[source] = time.time()
    
    async def _fetch_rockflow(self, symbol: str, market: str) -> Optional[Dict]:
        """从 Rockflow 获取数据"""
        source = "rockflow"
        await self._rate_limit_wait(source)
        
        config = self.data_sources[source]
        url = f"{config['url']}/market/tick/latest"
        params = {"symbol": symbol, "market": market}
        headers = {"X-API-Key": config["api_key"]}
        
        try:
            async with self.session.get(url, params=params, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if data.get("code") == 200:
                    quote = data.get("data", {}).get("data", {})
                    return {
                        "symbol": symbol,
                        "price": quote.get("tradePrice", 0),
                        "change_pct": quote.get("changePercent", 0),  # 已经是百分比形式
                        "volume": quote.get("volume", 0),
                        "source": source,
                        "timestamp": datetime.now().isoformat(),
                    }
        except Exception as e:
            print(f"Rockflow 获取 {symbol} 失败: {e}")
        
        return None
    
    async def _fetch_sina(self, symbol: str) -> Optional[Dict]:
        """从新浪获取 A股数据"""
        source = "sina"
        await self._rate_limit_wait(source)
        
        config = self.data_sources[source]
        url = f"{config['url']}{symbol}"
        
        try:
            async with self.session.get(url, timeout=5) as resp:
                text = await resp.text()
                # 解析新浪数据格式
                # var hq_str_sh603259="药明康德,103.78,102.95,..."
                if '=' in text and '"' in text:
                    parts = text.split('"')[1].split(',')
                    if len(parts) >= 4:
                        name = parts[0]
                        current = float(parts[3]) if parts[3] else 0
                        prev_close = float(parts[2]) if parts[2] else 0
                        change_pct = ((current - prev_close) / prev_close * 100) if prev_close > 0 else 0
                        
                        return {
                            "symbol": symbol,
                            "name": name,
                            "price": current,
                            "change_pct": change_pct,
                            "source": source,
                            "timestamp": datetime.now().isoformat(),
                        }
        except Exception as e:
            print(f"新浪获取 {symbol} 失败: {e}")
        
        return None
    
    async def _fetch_tencent(self, symbol: str) -> Optional[Dict]:
        """从腾讯获取 A股数据"""
        source = "tencent"
        await self._rate_limit_wait(source)
        
        config = self.data_sources[source]
        # 腾讯格式: sh603259
        url = f"{config['url']}{symbol}"
        
        try:
            async with self.session.get(url, timeout=5) as resp:
                text = await resp.text()
                # 解析腾讯数据格式
                # v_sh603259="1~药明康德~603259~103.78~..."
                if '~' in text:
                    parts = text.split('~')
                    if len(parts) >= 5:
                        name = parts[1]
                        current = float(parts[3]) if parts[3] else 0
                        prev_close = float(parts[4]) if parts[4] else 0
                        change_pct = float(parts[5]) if parts[5] else 0
                        
                        return {
                            "symbol": symbol,
                            "name": name,
                            "price": current,
                            "change_pct": change_pct,
                            "source": source,
                            "timestamp": datetime.now().isoformat(),
                        }
        except Exception as e:
            print(f"腾讯获取 {symbol} 失败: {e}")
        
        return None
    
    async def fetch_one(self, symbol: str, market: str = "US") -> Optional[Dict]:
        """获取单个股票数据"""
        # 确定数据源
        if market == "US" or market == "HK":
            return await self._fetch_rockflow(symbol, market)
        elif market == "A":
            # 优先使用新浪，失败则用腾讯
            result = await self._fetch_sina(symbol)
            if result is None:
                result = await self._fetch_tencent(symbol)
            return result
        
        return None
    
    async def fetch_batch(self, symbols: List[Tuple[str, str]], max_concurrent: int = None) -> List[Dict]:
        """
        并发获取多个股票数据
        
        Args:
            symbols: [(symbol, market), ...]
            max_concurrent: 最大并发数
        
        Returns:
            List[Dict]: 股票数据列表
        """
        if max_concurrent is None:
            max_concurrent = self.max_concurrent
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(symbol: str, market: str):
            async with semaphore:
                # 添加随机延迟避免被封
                await asyncio.sleep(random.uniform(0.1, 0.3))
                return await self.fetch_one(symbol, market)
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            tasks = [fetch_with_semaphore(symbol, market) for symbol, market in symbols]
            results = await asyncio.gather(*tasks)
        
        return [r for r in results if r is not None]
    
    async def fetch_all_markets(self) -> Dict[str, List[Dict]]:
        """获取所有市场数据"""
        results = {}
        
        # 美股
        us_symbols = [(s, "US") for s in self.symbol_mapping["US"].keys()]
        us_data = await self.fetch_batch(us_symbols)
        results["US"] = us_data
        
        # 港股
        hk_symbols = [(s, "HK") for s in self.symbol_mapping["HK"].keys()]
        hk_data = await self.fetch_batch(hk_symbols)
        results["HK"] = hk_data
        
        # A股
        a_symbols = [(s, "A") for s in self.symbol_mapping["A"].keys()]
        a_data = await self.fetch_batch(a_symbols)
        results["A"] = a_data
        
        return results

# 同步接口
def fetch_quotes_sync(symbols: List[Tuple[str, str]]) -> List[Dict]:
    """同步获取股票数据"""
    fetcher = ConcurrentFetcher()
    return asyncio.run(fetcher.fetch_batch(symbols))

def fetch_all_markets_sync() -> Dict[str, List[Dict]]:
    """同步获取所有市场数据"""
    fetcher = ConcurrentFetcher()
    return asyncio.run(fetcher.fetch_all_markets())

if __name__ == "__main__":
    print("测试并发获取器...")
    
    # 测试数据
    symbols = [
        ("NBIS", "US"),
        ("ARM", "US"),
        ("02513.HK", "HK"),
        ("00100.HK", "HK"),
    ]
    
    start = time.time()
    results = fetch_quotes_sync(symbols)
    elapsed = time.time() - start
    
    print(f"\n获取 {len(results)} 个股票，耗时 {elapsed:.2f}秒\n")
    
    for r in results:
        print(f"{r['symbol']}: ${r['price']:.2f} ({r['change_pct']:+.2f}%) [来源: {r['source']}]")
