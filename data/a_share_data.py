import time
import asyncio
import aiohttp
import random
import os
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class DataSource:
    """数据源基类 (支持异步)"""
    name = "base"
    @classmethod
    async def get_quote_async(cls, session: aiohttp.ClientSession, code: str) -> Optional[Dict]:
        raise NotImplementedError
    @classmethod
    async def get_klines_async(cls, session: aiohttp.ClientSession, code: str, days: int = 60) -> Optional[List[Dict]]:
        raise NotImplementedError

class EastMoneySource(DataSource):
    """东方财富数据源"""
    name = "eastmoney"
    @classmethod
    async def get_quote_async(cls, session: aiohttp.ClientSession, code: str) -> Optional[Dict]:
        secid = f"1.{code}" if code.startswith('6') else f"0.{code}"
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {'secid': secid, 'fields': 'f43,f44,f45,f46,f47,f48,f58,f60,f169,f170'}
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                if data and 'data' in data and data['data']:
                    d = data['data']
                    return {
                        'symbol': code, 'price': d.get('f43', 0) / 100,
                        'open': d.get('f46', 0) / 100, 'high': d.get('f44', 0) / 100,
                        'low': d.get('f45', 0) / 100, 'volume': d.get('f47', 0),
                        'change_pct': d.get('f170', 0) / 100, 'source': 'eastmoney'
                    }
        except: pass
        return None

class SinaSource(DataSource):
    """新浪财经数据源"""
    name = "sina"
    @classmethod
    async def get_quote_async(cls, session: aiohttp.ClientSession, code: str) -> Optional[Dict]:
        symbol = f"sh{code}" if code.startswith('6') else f"sz{code}"
        url = f"https://hq.sinajs.cn/list={symbol}"
        headers = {'Referer': 'https://finance.sina.com.cn/'}
        try:
            async with session.get(url, headers=headers, timeout=10) as resp:
                text = await resp.text(encoding='gbk')
                if '=' in text:
                    raw = text.split('=')[1].strip('"').split(',')
                    if len(raw) >= 32:
                        return {
                            'symbol': code, 'open': float(raw[1]), 'price': float(raw[3]),
                            'high': float(raw[4]), 'low': float(raw[5]), 'volume': float(raw[8]),
                            'change_pct': (float(raw[3]) - float(raw[2])) / float(raw[2]) * 100 if float(raw[2]) > 0 else 0,
                            'source': 'sina'
                        }
        except: pass
        return None

class BaiduSource(DataSource):
    """百度财经数据源"""
    name = "baidu"
    @classmethod
    async def get_quote_async(cls, session: aiohttp.ClientSession, code: str) -> Optional[Dict]:
        symbol = ('sh' if code.startswith('6') else 'sz') + code
        url = f"https://api.stock.baidu.com/api/qt/stock/get?group=has_stock&format=json&stockId={symbol}"
        try:
            async with session.get(url, timeout=5) as resp:
                data = await resp.json()
                if data and 'data' in data and data['data']:
                    d = data['data'][0]
                    price = float(d.get('curPrice') or d.get('preClosePrice') or 0)
                    pre = float(d.get('preClosePrice') or price or 1)
                    return {
                        'symbol': code, 'price': price, 'open': float(d.get('openPrice') or price),
                        'high': float(d.get('highPrice') or price), 'low': float(d.get('lowPrice') or price),
                        'volume': float(d.get('volume') or 0), 'change_pct': (price - pre) / pre * 100,
                        'source': 'baidu'
                    }
        except: pass
        return None

class AkshareSource(DataSource):
    """Akshare 数据源"""
    name = "akshare"
    @classmethod
    async def get_quote_async(cls, session: aiohttp.ClientSession, code: str) -> Optional[Dict]:
        try:
            import akshare as ak
            df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
            row = df[df['代码'] == code]
            if not row.empty:
                r = row.iloc[0]
                return {
                    'symbol': code, 'price': float(r['最新价']), 'open': float(r['今开']),
                    'high': float(r['最高']), 'low': float(r['最低']), 'volume': float(r['成交量']),
                    'change_pct': float(r['涨跌幅']), 'source': 'akshare'
                }
        except: pass
        return None

DATA_SOURCES = [BaiduSource, SinaSource, EastMoneySource, AkshareSource]

class AShareDataFetcher:
    """小强 A 股数据获取器 (全异步竞速版)"""
    def __init__(self):
        self.cache = {}
        self.last_update = 0
        self.cache_ttl = 60

    async def get_realtime_quote_async(self, session: aiohttp.ClientSession, symbol: str) -> Optional[Dict]:
        code = symbol.replace(".SZ", "").replace(".SH", "")
        tasks = [source.get_quote_async(session, code) for source in DATA_SOURCES]
        for completed in asyncio.as_completed(tasks):
            result = await completed
            if result:
                result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return result
        return None

    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
        async def run():
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                return await self.get_realtime_quote_async(session, symbol)
        return asyncio.run(run())

    async def scan_all_async(self, symbols: List[str]) -> Dict[str, Dict]:
        results = {}
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            tasks = [self.get_realtime_quote_async(session, s) for s in symbols]
            quotes = await asyncio.gather(*tasks)
            for s, q in zip(symbols, quotes):
                if q: results[s] = q
        return results

    def scan_all(self, symbols: List[str] = None) -> Dict[str, Dict]:
        if symbols is None:
            symbols = ["300308.SZ", "300394.SZ", "300502.SZ", "002281.SZ", "300750.SZ"]
        return asyncio.run(self.scan_all_async(symbols))

    def get_market_summary(self) -> Dict:
        # 简化版市场概况，利用竞速接口
        return {"上证指数": {"price": 0, "change_pct": 0}} # 占位

if __name__ == "__main__":
    fetcher = AShareDataFetcher()
    print("🚀 小强 A 股异步竞速验证...")
    res = fetcher.get_realtime_quote("601988")
    print(f"结果: {res}")
