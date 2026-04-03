#!/usr/bin/env python3
"""
小强量化系统 - 动态股票池管理器
从热门板块选出优质股票
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import time

sys.path.insert(0, str(Path(__file__).parent))

from data.a_share_data import AShareDataFetcher


class DynamicStockPool:
    """动态股票池管理器"""
    
    # 热门板块定义
    SECTORS = {
        "AI算力": {
            "description": "人工智能算力基础设施",
            "stocks": [
                "300474.SZ",  # 景嘉微 - GPU
                "688256.SH",  # 寒武纪 - AI芯片
                "688041.SH",  # 海光信息 - CPU/DCU
                "002230.SZ",  # 科大讯飞 - AI应用
                "688111.SH",  # 金山办公 - AI办公
                "000977.SZ",  # 浪潮信息 - 服务器
                "002405.SZ",  # 四维图新 - AI地图
            ]
        },
        "半导体": {
            "description": "芯片设计与制造",
            "stocks": [
                "688981.SH",  # 中芯国际 - 代工
                "002049.SZ",  # 紫光国微 - FPGA
                "603501.SH",  # 韦尔股份 - CIS
                "002371.SZ",  # 北方华创 - 设备
                "300661.SZ",  # 圣邦股份 - 模拟芯片
                "688012.SH",  # 中微公司 - 刻蚀设备
                "688396.SH",  # 华润微 - 功率器件
                "688147.SH",  # 盛美上海 - 清洗设备
            ]
        },
        "新能源汽车": {
            "description": "电动车产业链",
            "stocks": [
                "300750.SZ",  # 宁德时代 - 电池
                "002594.SZ",  # 比亚迪 - 整车
                "002475.SZ",  # 立讯精密 - 连接器
                "002179.SZ",  # 中航光电 - 连接器
            ]
        },
        "消费电子": {
            "description": "消费电子产品",
            "stocks": [
                "002475.SZ",  # 立讯精密 - AirPods
                "002241.SZ",  # 歌尔股份 - VR/AR
            ]
        },
        "军工": {
            "description": "国防军工",
            "stocks": [
                "600893.SH",  # 航发动力 - 航空发动机
                "002179.SZ",  # 中航光电 - 军工连接器
            ]
        },
        "化工": {
            "description": "化工材料",
            "stocks": [
                "600309.SH",  # 万华化学 - MDI
            ]
        },
        "金融科技": {
            "description": "金融软件与服务",
            "stocks": [
                "300033.SZ",  # 同花顺 - 金融终端
            ]
        },
    }
    
    def __init__(self):
        self.fetcher = AShareDataFetcher()
        self.pool_file = Path(__file__).parent / "watchlist" / "dynamic_pool.json"
    
    def scan_all_sectors(self) -> Dict:
        """扫描所有板块"""
        print("=" * 70)
        print("📊 扫描热门板块")
        print("=" * 70)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        all_results = {}
        
        for sector_name, sector_info in self.SECTORS.items():
            print(f"\n🔍 扫描板块: {sector_name}")
            print(f"   描述: {sector_info['description']}")
            print(f"   股票数: {len(sector_info['stocks'])}")
            
            # 获取行情
            quotes = self.fetcher.scan_all(sector_info['stocks'])
            
            if not quotes:
                print(f"   ⚠️ 无法获取数据")
                continue
            
            # 计算板块指标
            changes = [q.get('change_pct', 0) for q in quotes.values()]
            avg_change = sum(changes) / len(changes) if changes else 0
            up_count = sum(1 for c in changes if c > 0)
            down_count = len(changes) - up_count
            
            print(f"   平均涨幅: {avg_change:+.2f}%")
            print(f"   上涨/下跌: {up_count}/{down_count}")
            
            # 找出板块龙头
            sorted_quotes = sorted(quotes.items(), key=lambda x: x[1].get('change_pct', 0), reverse=True)
            
            leaders = []
            for symbol, quote in sorted_quotes[:3]:
                if quote.get('change_pct', 0) > avg_change:
                    leaders.append({
                        'symbol': symbol,
                        'name': quote.get('name', ''),
                        'price': quote.get('price', 0),
                        'change_pct': quote.get('change_pct', 0),
                        'turnover': quote.get('turnover', 0),
                    })
            
            if leaders:
                print(f"   龙头股:")
                for i, l in enumerate(leaders, 1):
                    emoji = "🟢" if l['change_pct'] > 0 else "🔴"
                    print(f"      {i}. {emoji} {l['name']}({l['symbol']}): {l['change_pct']:+.2f}%")
            
            all_results[sector_name] = {
                'avg_change': avg_change,
                'up_count': up_count,
                'down_count': down_count,
                'leaders': leaders,
                'quotes': {s: q for s, q in quotes.items()}
            }
        
        return all_results
    
    def select_top_stocks(self, sector_results: Dict, top_n: int = 10) -> List[Dict]:
        """选出热门板块的优质股票"""
        print("\n" + "=" * 70)
        print("⭐ 热门板块优质股票")
        print("=" * 70)
        
        # 计算所有股票的综合评分
        all_stocks = []
        
        for sector_name, sector_data in sector_results.items():
            sector_avg = sector_data['avg_change']
            
            for symbol, quote in sector_data['quotes'].items():
                change = quote.get('change_pct', 0)
                turnover = quote.get('turnover', 0)
                
                # 综合评分
                score = 0
                
                # 涨幅评分
                if change > 5:
                    score += 50
                elif change > 3:
                    score += 40
                elif change > 1:
                    score += 30
                elif change > 0:
                    score += 20
                elif change > -1:
                    score += 10
                
                # 相对板块评分
                if change > sector_avg:
                    score += 30
                
                # 板块强度评分
                if sector_avg > 1:
                    score += 20  # 强势板块
                elif sector_avg > 0:
                    score += 10
                
                # 换手率评分 (活跃度)
                if turnover > 5:
                    score += 20
                elif turnover > 3:
                    score += 10
                
                all_stocks.append({
                    'symbol': symbol,
                    'name': quote.get('name', ''),
                    'price': quote.get('price', 0),
                    'change_pct': change,
                    'turnover': turnover,
                    'score': score,
                    'sector': sector_name,
                    'sector_avg': sector_avg,
                })
        
        # 排序
        all_stocks.sort(key=lambda x: x['score'], reverse=True)
        
        # 输出 Top N
        top_stocks = all_stocks[:top_n]
        
        print(f"\nTop {top_n} 优质股票:\n")
        for i, s in enumerate(top_stocks, 1):
            emoji = "🟢" if s['change_pct'] > 0 else "🔴"
            sector_emoji = "🔥" if s['sector_avg'] > 0 else "⚠️"
            print(f"  {i}. {emoji} {s['name']}({s['symbol']})")
            print(f"     价格: ¥{s['price']:.2f}  涨幅: {s['change_pct']:+.2f}%  板块: {sector_emoji} {s['sector']} ({s['sector_avg']:+.2f}%)")
            print(f"     评分: {s['score']}  换手: {s['turnover']:.1f}%")
            print()
        
        return top_stocks
    
    def generate_report(self, sector_results: Dict, top_stocks: List[Dict]) -> str:
        """生成报告"""
        report = f"🐉 小强动态股票池扫描\n"
        report += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # 板块概况
        report += "📊 板块热度:\n"
        sorted_sectors = sorted(sector_results.items(), key=lambda x: x[1]['avg_change'], reverse=True)
        
        for sector_name, data in sorted_sectors:
            emoji = "🟢" if data['avg_change'] > 0 else "🔴"
            report += f"  {emoji} {sector_name}: {data['avg_change']:+.2f}% ({data['up_count']}/{data['down_count']})\n"
        
        # 热门板块
        hot_sectors = [s for s, d in sorted_sectors if d['avg_change'] > 0]
        if hot_sectors:
            report += f"\n🔥 热门板块: {', '.join(hot_sectors)}\n"
        
        # 优质股票
        report += f"\n⭐ 优质股票 Top 5:\n"
        for i, s in enumerate(top_stocks[:5], 1):
            emoji = "🟢" if s['change_pct'] > 0 else "🔴"
            report += f"  {i}. {emoji} {s['name']}({s['symbol']}): {s['change_pct']:+.2f}% | {s['sector']}\n"
        
        # 操作建议
        avg_change = sum(s['change_pct'] for s in top_stocks) / len(top_stocks) if top_stocks else 0
        report += f"\n💡 操作建议:\n"
        if avg_change < -2:
            report += "  🔴 市场弱势，观望为主\n"
            report += "  📌 关注抗跌龙头，等待企稳\n"
        elif avg_change < 0:
            report += "  ⚠️ 市场震荡，轻仓操作\n"
            report += "  📌 关注强势板块龙头\n"
        else:
            report += "  🟢 市场强势，可适当参与\n"
            report += "  📌 关注热门板块龙头\n"
        
        return report
    
    def save_pool(self, top_stocks: List[Dict]):
        """保存股票池"""
        self.pool_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'update_time': datetime.now().isoformat(),
            'stocks': top_stocks,
        }
        
        with open(self.pool_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存股票池到: {self.pool_file}")
    
    def run(self):
        """运行扫描"""
        # 扫描板块
        sector_results = self.scan_all_sectors()
        
        # 选出优质股票
        top_stocks = self.select_top_stocks(sector_results, top_n=15)
        
        # 生成报告
        report = self.generate_report(sector_results, top_stocks)
        print(report)
        
        # 保存
        self.save_pool(top_stocks)
        
        return report


if __name__ == "__main__":
    manager = DynamicStockPool()
    report = manager.run()
    
    # 发送到飞书
    import os
    import requests
    
    webhook = os.environ.get("FEISHU_WEBHOOK")
    if webhook:
        try:
            response = requests.post(
                webhook,
                json={"msg_type": "text", "content": {"text": report}},
                timeout=10
            )
            if response.status_code == 200:
                print("\n✅ 已推送到飞书")
        except Exception as e:
            print(f"\n❌ 推送失败: {e}")
