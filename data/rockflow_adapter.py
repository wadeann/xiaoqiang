#!/usr/bin/env python3
"""
小强量化系统 - 数据适配器
将 Rockflow API 数据转换为 qlib 格式
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


class RockflowAdapter:
    """Rockflow API 数据适配器"""
    
    def __init__(self, api_key: str, base_url: str = "https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def get_quote(self, symbol: str, market: str = "US") -> Optional[Dict]:
        """获取实时行情"""
        url = f"{self.base_url}/market/tick/latest"
        params = {"symbol": symbol, "market": market}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                return data["data"]["data"]
            return None
        except Exception as e:
            print(f"获取行情失败: {e}")
            return None
    
    def get_assets(self) -> Optional[Dict]:
        """获取账户资产"""
        url = f"{self.base_url}/assets"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                acc = data["data"]["data"]["broker"]["account"][0]
                return {
                    "total": acc.get("totalAssets", 0),
                    "cash": acc.get("availableCash", {}).get("USD", 0),
                    "buying_power": acc.get("buyingPower", 0)
                }
            return None
        except Exception as e:
            print(f"获取资产失败: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        url = f"{self.base_url}/positions"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                return data["data"]["data"]
            return []
        except Exception as e:
            print(f"获取持仓失败: {e}")
            return []
    
    def place_order(self, symbol: str, market: str, side: str, quantity: int, 
                    order_type: str = "MARKET_ORDER", price: Optional[float] = None) -> Optional[Dict]:
        """下单"""
        url = f"{self.base_url}/orders"
        
        data = {
            "market": market,
            "symbol": symbol,
            "instrument": "STOCK",
            "orderType": order_type,
            "quantity": quantity,
            "side": side,
            "validity": "GOOD_FOR_DAY",
            "session": "TRADING_SESSION"
        }
        
        if order_type == "LIMIT_ORDER" and price:
            data["price"] = price
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=10)
            result = response.json()
            
            if result.get("code") == 200:
                return result["data"]
            return None
        except Exception as e:
            print(f"下单失败: {e}")
            return None
    
    def to_qlib_format(self, quote: Dict) -> Dict:
        """转换为 qlib 格式"""
        return {
            "instrument": quote.get("symbol"),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "open": quote.get("open"),
            "close": quote.get("tradePrice") or quote.get("close"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "volume": quote.get("volume"),
            "change_pct": quote.get("changePercent", 0)
        }


# 测试代码
if __name__ == "__main__":
    from config import API_KEY
    
    adapter = RockflowAdapter(API_KEY)
    
    # 测试获取行情
    quote = adapter.get_quote("NVDA", "US")
    if quote:
        print(f"NVDA 行情: {adapter.to_qlib_format(quote)}")
    
    # 测试获取资产
    assets = adapter.get_assets()
    if assets:
        print(f"账户资产: {assets}")
