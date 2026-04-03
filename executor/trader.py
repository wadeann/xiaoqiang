#!/usr/bin/env python3
"""
小强量化系统 - 交易执行器
将策略信号转化为实际交易
"""

import json
import requests
from typing import Dict, List, Optional
from datetime import datetime


class Trader:
    """交易执行器"""
    
    def __init__(self, api_key: str, base_url: str = "https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
        
        # 交易历史
        self.trade_history = []
    
    def get_account(self) -> Optional[Dict]:
        """获取账户信息"""
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
            print(f"获取账户失败: {e}")
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
    
    def get_quote(self, symbol: str, market: str = "US") -> Optional[Dict]:
        """获取行情"""
        url = f"{self.base_url}/market/tick/latest"
        params = {"symbol": symbol, "market": market}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                d = data["data"]["data"]
                return {
                    "symbol": d.get("symbol") or symbol,
                    "price": d.get("tradePrice") or d.get("close"),
                    "change_pct": d.get("changePercent", 0)
                }
            return None
        except Exception as e:
            print(f"获取行情失败: {e}")
            return None
    
    def place_order(self, symbol: str, market: str, side: str, quantity: int,
                   order_type: str = "MARKET_ORDER", price: Optional[float] = None) -> Optional[Dict]:
        """
        下单
        
        Args:
            symbol: 标的代码
            market: 市场 (US/HK)
            side: 买卖方向 (BUY/SELL)
            quantity: 数量
            order_type: 订单类型
            price: 限价单价格
        
        Returns:
            订单结果
        """
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
                order_info = {
                    "symbol": symbol,
                    "market": market,
                    "side": side,
                    "quantity": quantity,
                    "order_type": order_type,
                    "status": "SUBMITTED",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self.trade_history.append(order_info)
                print(f"✅ 下单成功: {side} {symbol} {quantity}股")
                return order_info
            else:
                print(f"❌ 下单失败: {result}")
                return None
        except Exception as e:
            print(f"下单异常: {e}")
            return None
    
    def execute_signals(self, signals: List[Dict], max_position_pct: float = 0.3) -> List[Dict]:
        """
        执行交易信号
        
        Args:
            signals: 交易信号列表
            max_position_pct: 单只标的最大仓位比例
        
        Returns:
            执行结果列表
        """
        print("\n" + "=" * 60)
        print("📤 执行交易信号")
        print("=" * 60)
        
        # 获取账户信息
        account = self.get_account()
        if not account:
            print("❌ 无法获取账户信息")
            return []
        
        print(f"账户资金: ${account['cash']:,.0f}")
        print(f"总资产: ${account['total']:,.0f}")
        
        results = []
        
        for signal in signals:
            symbol = signal.get("symbol")
            market = signal.get("market", "US")
            action = signal.get("action")
            price = signal.get("price")
            
            if not symbol or not price:
                continue
            
            if action == "BUY":
                # 计算仓位
                position_value = account["total"] * max_position_pct
                quantity = int(position_value / price)
                
                if quantity < 1:
                    print(f"⚠️ {symbol}: 资金不足，跳过")
                    continue
                
                # 下单
                result = self.place_order(symbol, market, "BUY", quantity)
                if result:
                    results.append(result)
            
            elif action == "SELL":
                # 获取持仓
                positions = self.get_positions()
                for pos in positions:
                    if pos.get("symbol") == symbol:
                        quantity = pos.get("quantity", 0)
                        if quantity > 0:
                            result = self.place_order(symbol, market, "SELL", quantity)
                            if result:
                                results.append(result)
                        break
        
        print("=" * 60)
        return results
    
    def get_pending_orders(self) -> List[Dict]:
        """获取待成交订单"""
        url = f"{self.base_url}/orders?filled=false"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                return data["data"]["data"]
            return []
        except Exception as e:
            print(f"获取订单失败: {e}")
            return []
    
    def get_trade_summary(self) -> Dict:
        """获取交易统计"""
        return {
            "total_trades": len(self.trade_history),
            "buy_trades": len([t for t in self.trade_history if t["side"] == "BUY"]),
            "sell_trades": len([t for t in self.trade_history if t["side"] == "SELL"]),
            "trades": self.trade_history
        }


# 测试代码
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from data.rockflow_config import API_KEY
    
    trader = Trader(API_KEY)
    
    # 测试获取账户
    print("获取账户信息...")
    account = trader.get_account()
    if account:
        print(f"  总资产: ${account['total']:,.2f}")
        print(f"  现金: ${account['cash']:,.2f}")
    
    # 测试获取持仓
    print("\n获取持仓...")
    positions = trader.get_positions()
    print(f"  持仓数量: {len(positions)}")
    
    # 测试获取待成交订单
    print("\n获取待成交订单...")
    orders = trader.get_pending_orders()
    print(f"  待成交订单: {len(orders)}")
