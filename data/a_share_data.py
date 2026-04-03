#!/usr/bin/env python3
"""
小强量化系统 - A股数据获取模块 (多数据源版)
支持东方财富、新浪、腾讯、网易四个数据源，自动降级
"""

import time
import random
import re
import requests
from typing import Dict, List, Optional
from datetime import datetime


class DataSource:
    """数据源基类"""
    name = "base"
    rate_limit = 100  # 每分钟请求限制
    last_request_time = 0
    
    @classmethod
    def get_quote(cls, code: str) -> Optional[Dict]:
        raise NotImplementedError
    
    @classmethod
    def get_quotes_batch(cls, codes: List[str]) -> Dict[str, Dict]:
        """批量获取行情"""
        quotes = {}
        for code in codes:
            quote = cls.get_quote(code)
            if quote:
                quotes[code] = quote
            time.sleep(0.1)  # 避免限流
        return quotes
    
    @classmethod
    def wait_for_rate_limit(cls):
        """等待以避免限流"""
        elapsed = time.time() - cls.last_request_time
        min_interval = 60.0 / cls.rate_limit
        
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        cls.last_request_time = time.time()


class EastMoneySource(DataSource):
    """东方财富数据源"""
    name = "eastmoney"
    rate_limit = 100
    
    @classmethod
    def get_quote(cls, code: str) -> Optional[Dict]:
        cls.wait_for_rate_limit()
        
        # 解析股票代码
        if '.' in code:
            pure_code, market = code.split('.')
        else:
            pure_code = code
            market = 'SH' if code.startswith('6') else 'SZ'
        
        secid = f"1.{pure_code}" if market in ['SH', 'sh'] else f"0.{pure_code}"
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            'secid': secid,
            'fields': 'f43,f44,f45,f46,f47,f48,f58,f60,f169,f170'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        }
        
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            if data and 'data' in data and data['data']:
                d = data['data']
                return {
                    'symbol': code,
                    'market': 'CN',
                    'price': d.get('f43', 0) / 100 if d.get('f43') else 0,
                    'open': d.get('f46', 0) / 100 if d.get('f46') else 0,
                    'high': d.get('f44', 0) / 100 if d.get('f44') else 0,
                    'low': d.get('f45', 0) / 100 if d.get('f45') else 0,
                    'volume': d.get('f47', 0),
                    'amount': d.get('f48', 0),
                    'change_pct': d.get('f170', 0) / 100 if d.get('f170') else 0,
                    'source': 'eastmoney'
                }
        except Exception as e:
            pass
        
        return None


class SinaSource(DataSource):
    """新浪财经数据源"""
    name = "sina"
    rate_limit = 200
    
    @classmethod
    def get_quote(cls, code: str) -> Optional[Dict]:
        cls.wait_for_rate_limit()
        
        # 解析股票代码
        if '.' in code:
            pure_code, market = code.split('.')
        else:
            pure_code = code
            market = 'SH' if code.startswith('6') else 'SZ'
        
        symbol = f"sh{pure_code}" if market in ['SH', 'sh'] else f"sz{pure_code}"
        url = f"https://hq.sinajs.cn/list={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'gbk'
            
            if resp.text:
                match = re.search(r'="([^"]+)"', resp.text)
                if match:
                    data = match.group(1).split(',')
                    if len(data) >= 32:
                        return {
                            'symbol': code,
                            'market': 'CN',
                            'name': data[0],
                            'open': float(data[1]) if data[1] else 0,
                            'price': float(data[3]) if data[3] else 0,
                            'high': float(data[4]) if data[4] else 0,
                            'low': float(data[5]) if data[5] else 0,
                            'volume': float(data[8]) if data[8] else 0,
                            'amount': float(data[9]) if data[9] else 0,
                            'change_pct': round((float(data[3]) - float(data[2])) / float(data[2]) * 100, 2) if float(data[2]) > 0 else 0,
                            'source': 'sina'
                        }
        except Exception as e:
            pass
        
        return None
    
    @classmethod
    def get_quotes_batch(cls, codes: List[str]) -> Dict[str, Dict]:
        """批量获取行情 (新浪支持批量)"""
        # 构建请求列表
        symbols = []
        for code in codes:
            if '.' in code:
                pure_code, market = code.split('.')
            else:
                pure_code = code
                market = 'SH' if code.startswith('6') else 'SZ'
            symbols.append(f"sh{pure_code}" if market in ['SH', 'sh'] else f"sz{pure_code}")
        
        url = f"https://hq.sinajs.cn/list={','.join(symbols)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        }
        
        quotes = {}
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'gbk'
            
            lines = resp.text.strip().split("\n")
            
            for i, line in enumerate(lines):
                if i >= len(codes):
                    break
                
                code = codes[i]
                match = re.search(r'="([^"]+)"', line)
                
                if not match:
                    continue
                
                data = match.group(1).split(',')
                if len(data) < 32:
                    continue
                
                try:
                    quotes[code] = {
                        'symbol': code,
                        'market': 'CN',
                        'name': data[0],
                        'open': float(data[1]) if data[1] else 0,
                        'price': float(data[3]) if data[3] else 0,
                        'high': float(data[4]) if data[4] else 0,
                        'low': float(data[5]) if data[5] else 0,
                        'volume': float(data[8]) if data[8] else 0,
                        'amount': float(data[9]) if data[9] else 0,
                        'change_pct': round((float(data[3]) - float(data[2])) / float(data[2]) * 100, 2) if float(data[2]) > 0 else 0,
                        'source': 'sina'
                    }
                except:
                    pass
            
        except Exception as e:
            print(f"Sina batch error: {e}")
        
        return quotes


class TencentSource(DataSource):
    """腾讯财经数据源"""
    name = "tencent"
    rate_limit = 150
    
    @classmethod
    def get_quote(cls, code: str) -> Optional[Dict]:
        cls.wait_for_rate_limit()
        
        if '.' in code:
            pure_code, market = code.split('.')
        else:
            pure_code = code
            market = 'SH' if code.startswith('6') else 'SZ'
        
        symbol = f"sh{pure_code}" if market in ['SH', 'sh'] else f"sz{pure_code}"
        url = f"https://web.sqt.gtimg.cn/q={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://gu.qq.com/'
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'gbk'
            
            if resp.text:
                data = resp.text.split('~')
                if len(data) >= 45:
                    return {
                        'symbol': code,
                        'market': 'CN',
                        'name': data[1],
                        'price': float(data[3]),
                        'open': float(data[5]),
                        'high': float(data[33]),
                        'low': float(data[34]),
                        'volume': float(data[6]),
                        'amount': float(data[37]),
                        'change_pct': float(data[32]),
                        'source': 'tencent'
                    }
        except Exception as e:
            pass
        
        return None


class NetEaseSource(DataSource):
    """网易财经数据源"""
    name = "netease"
    rate_limit = 100
    
    @classmethod
    def get_quote(cls, code: str) -> Optional[Dict]:
        # 网易接口不稳定，降级到东财
        return EastMoneySource.get_quote(code)


# 数据源列表 (按优先级排序)
DATA_SOURCES = [SinaSource, EastMoneySource, TencentSource, NetEaseSource]


class AShareDataFetcher:
    """A股数据获取器 - 多数据源版"""
    
    def __init__(self, preferred_source: str = "sina"):
        self.cache = {}
        self.last_update = 0
        self.cache_ttl = 60  # 缓存60秒
        self.preferred_source = preferred_source
        self.session = requests.Session()
    
    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """获取单只股票实时行情"""
        for source in DATA_SOURCES:
            result = source.get_quote(symbol)
            if result:
                result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return result
        return None
    
    def scan_all(self, symbols: List[str] = None) -> Dict[str, Dict]:
        """批量获取行情"""
        # 检查缓存
        current_time = time.time()
        if self.cache and (current_time - self.last_update) < self.cache_ttl:
            cached_results = {s: self.cache.get(s) for s in (symbols or []) if s in self.cache}
            if len(cached_results) >= len(symbols) * 0.8 if symbols else True:
                return cached_results
        
        if symbols is None:
            # 默认 A股标的 (含光模块/光通信板块)
            symbols = [
                # AI 芯片
                "300474.SZ",  # 景嘉微
                "688981.SH",  # 中芯国际
                "002049.SZ",  # 紫光国微
                # 光模块/光通信
                "300308.SZ",  # 中际旭创
                "300394.SZ",  # 天孚通信
                "300502.SZ",  # 新易盛
                "002281.SZ",  # 光迅科技
                "300570.SZ",  # 太辰光
                "688205.SH",  # 德科立
                "688195.SH",  # 腾景科技
                "688307.SH",  # 中润光学
                # AI 算力
                "000977.SZ",  # 浪潮信息
                "002230.SZ",  # 科大讯飞
                "300033.SZ",  # 同花顺
                # 半导体
                "603501.SH",  # 韦尔股份
                "002371.SZ",  # 北方华创
                "300661.SZ",  # 圣邦股份
                # 新能源
                "300750.SZ",  # 宁德时代
                "002594.SZ",  # 比亚迪
            ]
        
        quotes = {}
        
        # 分批处理，每批最多 50 只
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            # 优先使用新浪批量接口
            batch_quotes = SinaSource.get_quotes_batch(batch)
            quotes.update(batch_quotes)
            
            # 对于失败的，尝试其他数据源
            failed_symbols = [s for s in batch if s not in quotes]
            
            if failed_symbols:
                for source in [EastMoneySource, TencentSource]:
                    for symbol in failed_symbols[:]:
                        result = source.get_quote(symbol)
                        if result:
                            quotes[symbol] = result
                            result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            failed_symbols.remove(symbol)
                    if not failed_symbols:
                        break
        
        # 更新缓存
        self.cache = quotes
        self.last_update = current_time
        
        return quotes
    
    def get_market_summary(self) -> Dict:
        """获取市场概况"""
        # 主要指数代码
        indices = {
            "s_sh000001": ("000001.SH", "上证指数"),
            "s_sz399001": ("399001.SZ", "深证成指"),
            "s_sz399006": ("399006.SZ", "创业板指"),
            "s_sh000688": ("000688.SH", "科创50"),
        }
        
        summary = {}
        
        try:
            # 新浪指数接口
            codes_str = ",".join(indices.keys())
            url = f"https://hq.sinajs.cn/list={codes_str}"
            headers = {
                "Referer": "http://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0"
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            response.encoding = "gbk"
            
            lines = response.text.strip().split("\n")
            
            for i, (code_key, (code, name)) in enumerate(indices.items()):
                if i < len(lines):
                    match = re.search(r'="([^"]+)"', lines[i])
                    if match:
                        data = match.group(1).split(",")
                        if len(data) >= 4:
                            summary[name] = {
                                "price": float(data[1]) if data[1] else 0,
                                "change_pct": float(data[3]) if data[3] else 0,
                            }
        except Exception as e:
            print(f"获取市场概况失败: {e}")
        
        return summary
    
    def get_hot_stocks(self, top_n: int = 10) -> List[Dict]:
        """获取热门股票 (涨幅榜) - 需要其他数据源"""
        return []


# 测试代码
if __name__ == "__main__":
    fetcher = AShareDataFetcher()
    
    print("=" * 60)
    print("A股数据测试 (多数据源版)")
    print("=" * 60)
    
    # 测试市场概况
    print("\n📊 市场概况:")
    summary = fetcher.get_market_summary()
    for name, data in summary.items():
        emoji = "🟢" if data['change_pct'] > 0 else "🔴"
        print(f"  {emoji} {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)")
    
    # 测试批量获取
    print("\n📈 监控标的行情:")
    quotes = fetcher.scan_all()
    for symbol, quote in list(quotes.items())[:5]:
        name = quote.get('name', '')
        print(f"  {name} ({symbol}): ¥{quote['price']:.2f} ({quote['change_pct']:+.2f}%)")
    
    print(f"\n数据源统计:")
    source_count = {}
    for quote in quotes.values():
        source = quote.get('source', 'unknown')
        source_count[source] = source_count.get(source, 0) + 1
    for source, count in source_count.items():
        print(f"  {source}: {count} 只")
