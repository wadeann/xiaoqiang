#!/usr/bin/env python3
"""
数据源性能测试脚本
测试各数据源的响应时间和可用性
"""

import time
import sys
sys.path.insert(0, '/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang/data')

from a_share_data import AShareDataSource


def test_source_performance():
    """测试各数据源性能"""
    data_source = AShareDataSource(timeout=10, retry=1)
    
    # 测试代码
    test_codes = ['sh000001', 'sz399001', 'sh600519']
    
    # 测试各数据源
    sources = {
        'sina': data_source._get_from_sina,
        'tencent': data_source._get_from_tencent,
        'eastmoney': data_source._get_from_eastmoney
    }
    
    print("=" * 70)
    print("📊 数据源性能测试")
    print("=" * 70)
    
    results = {}
    
    for source_name, source_func in sources.items():
        print(f"\n🔍 测试数据源: {source_name.upper()}")
        print("-" * 70)
        
        source_results = []
        
        for code in test_codes:
            start_time = time.time()
            result = source_func(code)
            elapsed = (time.time() - start_time) * 1000  # 毫秒
            
            if result:
                source_results.append({
                    'code': code,
                    'success': True,
                    'time_ms': elapsed,
                    'name': result.get('name', ''),
                    'price': result.get('price', 0)
                })
                print(f"✅ {code} ({result.get('name', '')}): {result.get('price', 0):.2f} - {elapsed:.0f}ms")
            else:
                source_results.append({
                    'code': code,
                    'success': False,
                    'time_ms': elapsed
                })
                print(f"❌ {code}: 失败 - {elapsed:.0f}ms")
        
        success_count = sum(1 for r in source_results if r['success'])
        avg_time = sum(r['time_ms'] for r in source_results) / len(source_results)
        
        results[source_name] = {
            'success_rate': success_count / len(test_codes) * 100,
            'avg_time_ms': avg_time,
            'details': source_results
        }
        
        print(f"\n成功率: {success_count}/{len(test_codes)} ({success_count/len(test_codes)*100:.0f}%)")
        print(f"平均响应时间: {avg_time:.0f}ms")
    
    # 总结
    print("\n" + "=" * 70)
    print("📈 性能对比总结")
    print("=" * 70)
    print(f"{'数据源':<12} {'成功率':<10} {'平均响应时间':<15}")
    print("-" * 70)
    
    for source_name, data in results.items():
        print(f"{source_name.upper():<12} {data['success_rate']:.0f}%{'':<6} {data['avg_time_ms']:.0f}ms")
    
    # 推荐
    print("\n" + "=" * 70)
    best_source = min(results.items(), key=lambda x: x[1]['avg_time_ms'])
    print(f"🏆 最快数据源: {best_source[0].upper()} ({best_source[1]['avg_time_ms']:.0f}ms)")
    print("=" * 70)


if __name__ == "__main__":
    test_source_performance()
