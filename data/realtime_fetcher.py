#!/usr/bin/env python3
"""
小强量化系统 - 实时数据获取器
定时获取 Rockflow 行情数据并缓存
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class RealtimeFetcher:
    """实时数据获取器"""
    
    def __init__(self, api_key: str, cache_dir: str = "./data/cache"):
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 美股和港股标的
        self.us_tickers = ["NVDA", "TSLA", "ARM", "ASML", "PLTR", "MU", "TSM", "CRWV", "IREN", "NBIS", "BABA", "BIDU"]
        self.hk_tickers = ["00700.HK", "09988.HK", "09888.HK", "00981.HK", "02513.HK", "06869.HK", "00100.HK"]
    
    def get_quote(self, symbol: str, market: str = "US") -> Optional[Dict]:
        """获取实时行情"""
        url = f"https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1/market/tick/latest"
        headers = {"X-API-Key": self.api_key}
        params = {"symbol": symbol, "market": market}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                d = data["data"]["data"]
                return {
                    "symbol": d.get("symbol") or symbol,
                    "market": market,
                    "price": d.get("tradePrice") or d.get("close"),
                    "open": d.get("open"),
                    "high": d.get("high"),
                    "low": d.get("low"),
                    "close": d.get("close"),
                    "volume": d.get("volume", 0),
                    "change_pct": d.get("changePercent", 0),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            return None
        except Exception as e:
            print(f"获取 {symbol} 行情失败: {e}")
            return None
    
    def scan_all(self) -> Dict[str, Dict]:
        """扫描所有标的"""
        results = {}
        
        # 美股
        for symbol in self.us_tickers:
            quote = self.get_quote(symbol, "US")
            if quote:
                results[symbol] = quote
            time.sleep(0.3)  # 避免频率限制
        
        # 港股
        for symbol in self.hk_tickers:
            quote = self.get_quote(symbol, "HK")
            if quote:
                results[symbol] = quote
            time.sleep(0.3)
        
        return results
    
    def get_top_gainers(self, top_n: int = 3, min_change: float = 3.0) -> List[Dict]:
        """获取涨幅最大的标的"""
        all_quotes = self.scan_all()
        
        # 过滤涨幅大于阈值的
        gainers = [q for q in all_quotes.values() if q.get("change_pct", 0) >= min_change]
        
        # 按涨幅排序
        gainers.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
        
        return gainers[:top_n]
    
    def save_cache(self, data: Dict, filename: str = "latest_quotes.json"):
        """保存缓存"""
        cache_file = self.cache_dir / filename
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ 缓存已保存: {cache_file}")
    
    def load_cache(self, filename: str = "latest_quotes.json") -> Optional[Dict]:
        """加载缓存"""
        cache_file = self.cache_dir / filename
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def to_qlib_dataframe(self, quotes: Dict[str, Dict]):
        """转换为 qlib DataFrame 格式"""
        import pandas as pd
        
        records = []
        for symbol, quote in quotes.items():
            records.append({
                "instrument": symbol,
                "datetime": quote.get("timestamp"),
                "open": quote.get("open"),
                "close": quote.get("price") or quote.get("close"),
                "high": quote.get("high"),
                "low": quote.get("low"),
                "volume": quote.get("volume"),
                "change_pct": quote.get("change_pct")
            })
        
        df = pd.DataFrame(records)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index(["instrument", "datetime"])
        
        return df


# 测试代码
if __name__ == "__main__":
    from rockflow_config import API_KEY
    
    fetcher = RealtimeFetcher(API_KEY)
    
    print("扫描所有标的...")
    quotes = fetcher.scan_all()
    
    print(f"\n共获取 {len(quotes)} 只标的行情:")
    for symbol, quote in sorted(quotes.items(), key=lambda x: x[1].get("change_pct", 0), reverse=True)[:5]:
        print(f"  {symbol}: ${quote['price']:.2f} ({quote['change_pct']:+.2f}%)")
    
    # 保存缓存
    fetcher.save_cache(quotes)
    
    # 转换为 qlib 格式
    df = fetcher.to_qlib_dataframe(quotes)
    print(f"\nqlib DataFrame:\n{df.head()}")
