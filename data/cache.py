#!/usr/bin/env python3
"""
小强量化系统 - 数据缓存管理
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class DataCache:
    """数据缓存管理"""
    
    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存文件
        self.quotes_cache = self.cache_dir / "quotes_cache.json"
        self.history_cache = self.cache_dir / "history_cache.json"
        
        # 缓存过期时间 (秒)
        self.cache_ttl = 60  # 1分钟
    
    def get(self, key: str) -> Optional[Dict]:
        """获取缓存"""
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 检查是否过期
            if time.time() - data.get("timestamp", 0) > self.cache_ttl:
                return None
            
            return data.get("data")
        except Exception as e:
            print(f"读取缓存失败: {e}")
            return None
    
    def set(self, key: str, data: Dict):
        """设置缓存"""
        cache_file = self._get_cache_file(key)
        cache_data = {
            "timestamp": time.time(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": data
        }
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"写入缓存失败: {e}")
    
    def _get_cache_file(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.json"
    
    def clear(self, key: Optional[str] = None):
        """清除缓存"""
        if key:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()
        else:
            # 清除所有缓存
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "cache_dir": str(self.cache_dir),
            "cache_count": len(cache_files),
            "total_size_kb": total_size / 1024
        }


# 测试代码
if __name__ == "__main__":
    cache = DataCache()
    
    # 测试缓存
    test_data = {"NVDA": {"price": 175.0, "change_pct": 5.5}}
    
    print("设置缓存...")
    cache.set("test_quotes", test_data)
    
    print("获取缓存...")
    cached = cache.get("test_quotes")
    print(f"缓存数据: {cached}")
    
    print("\n缓存统计:")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n清除测试缓存...")
    cache.clear("test_quotes")
