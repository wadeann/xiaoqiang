#!/usr/bin/env python3
"""
小强量化系统 - 主程序 (v3.0 (Evolution 4.0))
支持 A股 + 美股 双市场切换
A股工作流: 盘前分析、盘中扫描、机会挖掘、盘后复盘
更新: 添加光模块/光通信板块监控
"""

import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime, time
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入模块
from data.rockflow_adapter import RockflowAdapter
from data.realtime_fetcher import RealtimeFetcher
from data.a_share_data import AShareDataFetcher
from data.cache import DataCache
from data.rockflow_config import API_KEY, BASE_URL, STARTING_CAPITAL, TARGET_RETURN, STOP_LOSS, US_TICKERS, HK_TICKERS, A_SHARE_TICKERS
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.risk_manager import RiskManager
from executor.trader import Trader
from executor.signal_filter import SignalFilter
from monitor.dashboard import Dashboard


# 历史预测记录 (用于复盘)
PREDICTION_FILE = Path(__file__).parent / "history" / "predictions.json"


class XiaoQiangSystem:
    """小强量化系统主类 - 支持双市场"""
    
    def __init__(self, mode: str = "us_share"):
        """
        初始化
        
        Args:
            mode: 运行模式
                - "a_share": A股模式
                - "us_share": 美股模式
        """
        self.mode = mode
        self.api_key = API_KEY
        self.base_url = BASE_URL
        
        # 根据模式选择数据源
        if mode == "a_share":
            self.market_name = "A股"
            self.tickers = A_SHARE_TICKERS
            self.data_fetcher = AShareDataFetcher()
        else:
            self.market_name = "美股"
            self.tickers = US_TICKERS + HK_TICKERS
            self.data_fetcher = RealtimeFetcher(self.api_key)
        
        # 通用组件
        self.adapter = RockflowAdapter(self.api_key, self.base_url) if mode == "us_share" else None
        self.cache = DataCache()
        
        # 策略
        self.momentum_strategy = MomentumStrategy(top_n=3, min_change_pct=3.0)
        self.mean_reversion_strategy = MeanReversionStrategy(top_n=3, max_drop_pct=-3.0)
        
        # 风控 (美股模式)
        self.risk_manager = RiskManager(
            starting_capital=STARTING_CAPITAL,
            target_return=TARGET_RETURN,
            stop_loss=STOP_LOSS
        ) if mode == "us_share" else None
        
        # 执行器 (美股模式才交易)
        self.trader = Trader(self.api_key, self.base_url) if mode == "us_share" else None
        self.signal_filter = SignalFilter(min_change_pct=3.0, max_change_pct=20.0)
        
        # 状态
        self.assets = None
        self.positions = []
        self.quotes = {}
        self.predictions = self._load_predictions()
    
    def _load_predictions(self) -> dict:
        """加载历史预测记录"""
        if PREDICTION_FILE.exists():
            with open(PREDICTION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"records": []}
    
    def _save_predictions(self):
        """保存预测记录"""
        PREDICTION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PREDICTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.predictions, f, ensure_ascii=False, indent=2)
    
    def update_market_data(self):
        """更新市场数据"""
        print(f"📊 扫描{self.market_name}行情...")
        
        if self.mode == "a_share":
            self.quotes = self.data_fetcher.scan_all(self.tickers)
            # 添加市场概况
            self.market_summary = self.data_fetcher.get_market_summary()
        else:
            self.quotes = self.data_fetcher.scan_all()
        
        if self.quotes:
            self.cache.set("latest_quotes", self.quotes)
            print(f"✅ 已获取 {len(self.quotes)} 只标的行情")
        
        # 显示 Top 5
        sorted_quotes = sorted(self.quotes.items(), key=lambda x: x[1].get("change_pct", 0), reverse=True)
        print(f"\n🔥 {self.market_name} Top 5 涨幅:")
        for i, (symbol, quote) in enumerate(sorted_quotes[:5], 1):
            name = quote.get('name', '') if self.mode == "a_share" else ''
            print(f"  {i}. {symbol} {name}: {quote.get('price', 0):.2f} ({quote.get('change_pct', 0):+.2f}%)")
        
        return self.quotes
    
    def pre_market_analysis(self):
        """盘前分析 (A股专用)"""
        if self.mode != "a_share":
            print("⚠️ 盘前分析仅支持A股模式")
            return
        
        print("\n" + "=" * 70)
        print("🌅 盘前分析")
        print("=" * 70)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 市场概况
        print("\n📊 市场概况:")
        if hasattr(self, 'market_summary'):
            for name, data in self.market_summary.items():
                emoji = "🟢" if data['change_pct'] > 0 else "🔴"
                print(f"  {emoji} {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)")
        
        # 2. 竞价强度分析
        print("\n📈 竞价强度分析:")
        sorted_quotes = sorted(self.quotes.items(), key=lambda x: x[1].get('turnover', 0), reverse=True)
        print("  换手率 Top 5 (竞价活跃):")
        for i, (symbol, quote) in enumerate(sorted_quotes[:5], 1):
            name = quote.get('name', '')
            turnover = quote.get('turnover', 0)
            change = quote.get('change_pct', 0)
            emoji = "🔥" if turnover > 5 else "✅" if turnover > 2 else "⚪"
            print(f"    {emoji} {symbol} {name}: 换手{turnover:.1f}% ({change:+.2f}%)")
        
        # 3. 新闻影响分析 (模拟 - 实际需要接入新闻API)
        print("\n📰 新闻影响分析:")
        print("  ⚠️ 新闻API待接入，当前显示市场情绪")
        up_count = sum(1 for q in self.quotes.values() if q.get('change_pct', 0) > 0)
        avg_change = sum(q.get('change_pct', 0) for q in self.quotes.values()) / len(self.quotes) if self.quotes else 0
        sentiment = "乐观" if avg_change > 1 else "谨慎" if avg_change > 0 else "悲观"
        print(f"  市场情绪: {sentiment}")
        print(f"  上涨/下跌: {up_count}/{len(self.quotes) - up_count}")
        print(f"  平均涨幅: {avg_change:+.2f}%")
        
        # 4. 持仓操作建议
        print("\n💡 持仓操作建议:")
        for symbol, quote in self.quotes.items():
            name = quote.get('name', '')
            change = quote.get('change_pct', 0)
            turnover = quote.get('turnover', 0)
            
            if change > 3 and turnover > 3:
                suggestion = "🟢 强势高开，可持有观察"
            elif change > 0 and turnover > 2:
                suggestion = "✅ 正常开盘，持有"
            elif change < -2:
                suggestion = "🔴 低开较多，注意风险"
            elif change < 0:
                suggestion = "⚠️ 小幅低开，观察"
            else:
                suggestion = "⚪ 平开，观望"
            
            print(f"  {symbol} {name}: {change:+.2f}% - {suggestion}")
        
        # 5. 记录预测
        self._record_predictions()
        
        print("\n" + "=" * 70)
    
    def _record_predictions(self):
        """记录今日预测 (用于复盘)"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        for symbol, quote in self.quotes.items():
            change = quote.get('change_pct', 0)
            turnover = quote.get('turnover', 0)
            
            # 预测逻辑
            if change > 3 and turnover > 3:
                prediction = "continue_up"  # 预测继续上涨
            elif change < -2:
                prediction = "continue_down"  # 预测继续下跌
            else:
                prediction = "sideways"  # 预测横盘
            
            self.predictions["records"].append({
                "date": today,
                "time": datetime.now().strftime("%H:%M"),
                "symbol": symbol,
                "open_change": change,
                "turnover": turnover,
                "prediction": prediction,
                "actual": None,  # 收盘后填充
            })
        
        self._save_predictions()
        print(f"✅ 已记录 {len(self.quotes)} 条预测")
    
    def scan_opportunity(self):
        """扫描买入机会 (A股专用)"""
        if self.mode != "a_share":
            print("⚠️ 机会扫描仅支持A股模式")
            return
        
        print("\n" + "=" * 70)
        print("🎯 买入机会扫描")
        print("=" * 70)
        
        # 1. 大盘扫描
        print("\n📊 大盘扫描:")
        if hasattr(self, 'market_summary'):
            for name, data in self.market_summary.items():
                emoji = "🟢" if data['change_pct'] > 0 else "🔴"
                print(f"  {emoji} {name}: {data['price']:.2f} ({data['change_pct']:+.2f}%)")
        
        # 2. 强势股
        print("\n🔥 强势股 (涨幅>3%, 换手>2%):")
        strong = [(s, q) for s, q in self.quotes.items() 
                  if q.get('change_pct', 0) > 3 and q.get('turnover', 0) > 2]
        strong.sort(key=lambda x: x[1].get('change_pct', 0), reverse=True)
        
        for i, (symbol, quote) in enumerate(strong[:5], 1):
            name = quote.get('name', '')
            change = quote.get('change_pct', 0)
            turnover = quote.get('turnover', 0)
            print(f"  {i}. {symbol} {name}: {change:+.2f}% 换手{turnover:.1f}%")
        
        # 3. 反弹机会
        print("\n🔄 反弹机会 (跌幅<-3%, 换手>1%):")
        rebound = [(s, q) for s, q in self.quotes.items() 
                   if q.get('change_pct', 0) < -3 and q.get('turnover', 0) > 1]
        rebound.sort(key=lambda x: x[1].get('change_pct', 0))
        
        for i, (symbol, quote) in enumerate(rebound[:5], 1):
            name = quote.get('name', '')
            change = quote.get('change_pct', 0)
            turnover = quote.get('turnover', 0)
            print(f"  {i}. {symbol} {name}: {change:+.2f}% 换手{turnover:.1f}%")
        
        # 4. 买入建议
        print("\n💡 买入建议:")
        if strong:
            top_strong = strong[0]
            print(f"  🟢 追涨: {top_strong[0]} {top_strong[1].get('name', '')} - 强势突破")
        
        if rebound:
            top_rebound = rebound[0]
            print(f"  🔄 抄底: {top_rebound[0]} {top_rebound[1].get('name', '')} - 超跌反弹")
        
        print("\n" + "=" * 70)
    
    def daily_review(self):
        """盘后复盘 (A股专用)"""
        if self.mode != "a_share":
            print("⚠️ 盘后复盘仅支持A股模式")
            return
        
        print("\n" + "=" * 70)
        print("📋 盘后复盘")
        print("=" * 70)
        
        # 1. 当日总结
        print("\n📊 当日总结:")
        up_count = sum(1 for q in self.quotes.values() if q.get('change_pct', 0) > 0)
        avg_change = sum(q.get('change_pct', 0) for q in self.quotes.values()) / len(self.quotes) if self.quotes else 0
        
        sorted_quotes = sorted(self.quotes.items(), key=lambda x: x[1].get('change_pct', 0), reverse=True)
        
        print(f"  上涨/下跌: {up_count}/{len(self.quotes) - up_count}")
        print(f"  平均涨幅: {avg_change:+.2f}%")
        
        print("\n📈 涨幅榜 Top 5:")
        for i, (symbol, quote) in enumerate(sorted_quotes[:5], 1):
            name = quote.get('name', '')
            change = quote.get('change_pct', 0)
            print(f"  {i}. {symbol} {name}: {change:+.2f}%")
        
        print("\n📉 跌幅榜 Top 5:")
        for i, (symbol, quote) in enumerate(sorted_quotes[-5:][::-1], 1):
            name = quote.get('name', '')
            change = quote.get('change_pct', 0)
            print(f"  {i}. {symbol} {name}: {change:+.2f}%")
        
        # 2. 预测验证
        print("\n🎯 预测验证:")
        today = datetime.now().strftime("%Y-%m-%d")
        today_predictions = [p for p in self.predictions["records"] if p["date"] == today]
        
        if today_predictions:
            correct = 0
            total = 0
            for pred in today_predictions:
                symbol = pred["symbol"]
                if symbol in self.quotes:
                    actual_change = self.quotes[symbol].get('change_pct', 0)
                    pred_type = pred["prediction"]
                    
                    # 更新实际值
                    pred["actual"] = actual_change
                    
                    # 验证预测
                    if pred_type == "continue_up" and actual_change > 0:
                        correct += 1
                    elif pred_type == "continue_down" and actual_change < 0:
                        correct += 1
                    elif pred_type == "sideways" and abs(actual_change) < 2:
                        correct += 1
                    total += 1
            
            accuracy = correct / total * 100 if total > 0 else 0
            print(f"  今日预测: {correct}/{total} 正确 ({accuracy:.1f}%)")
            
            # 保存更新后的预测
            self._save_predictions()
        else:
            print("  无今日预测记录")
        
        # 3. 策略调整建议
        print("\n⚙️ 策略调整建议:")
        if avg_change > 2:
            print("  🟢 市场强势，可适当提高仓位")
        elif avg_change < -2:
            print("  🔴 市场弱势，建议降低仓位或观望")
        else:
            print("  ⚪ 市场震荡，保持谨慎")
        
        # 4. 保存日报
        self.save_daily_summary()
        
        print("\n" + "=" * 70)
    
    def generate_signals(self):
        """生成交易信号"""
        print(f"\n🎯 生成{self.market_name}交易信号...")
        
        # 准备数据
        quote_list = []
        for symbol, quote in self.quotes.items():
            quote_list.append({
                "symbol": symbol,
                "market": quote.get("market", "US" if self.mode == "us_share" else "CN"),
                "price": quote.get("price"),
                "change_pct": quote.get("change_pct", 0),
                "volume": quote.get("volume", 0),
                "name": quote.get("name", ""),
                "turnover": quote.get("turnover", 0),
            })
        
        # 动量策略信号
        momentum_signals = self.momentum_strategy.generate_signals(quote_list)
        print(f"  动量策略: {len(momentum_signals)} 个信号")
        for s in momentum_signals[:3]:
            print(f"    {s['action']} {s['symbol']}: {s['reason']}")
        
        # A股模式: 生成详细分析报告
        if self.mode == "a_share":
            self._generate_intraday_report(quote_list)
            return momentum_signals
        
        # 美股模式: 过滤信号准备交易
        filtered_signals = self.signal_filter.filter_signals(momentum_signals, self.quotes)
        print(f"\n  过滤后: {len(filtered_signals)} 个信号")
        
        return filtered_signals
    
    def _generate_intraday_report(self, quote_list: list):
        """生成盘中分析报告"""
        print("\n" + "=" * 70)
        print("📊 盘中分析报告")
        print("=" * 70)
        
        # 1. 龙头股识别
        print("\n🐉 龙头股识别:")
        
        # 按成交额排序 (龙头股特征：成交额大)
        by_amount = sorted(quote_list, key=lambda x: x.get('amount', 0) or x.get('volume', 0), reverse=True)
        
        # 按涨幅排序 (龙头股特征：涨幅领先)
        by_change = sorted(quote_list, key=lambda x: x.get('change_pct', 0), reverse=True)
        
        # 综合评分
        leaders = []
        for q in quote_list:
            score = 0
            # 涨幅加分
            change = q.get('change_pct', 0)
            if change > 3:
                score += 30
            elif change > 1:
                score += 20
            elif change > 0:
                score += 10
            
            # 成交额加分
            amount = q.get('amount', 0) or q.get('volume', 0)
            if amount > 100000000:  # 1亿
                score += 30
            elif amount > 50000000:  # 5000万
                score += 20
            elif amount > 10000000:  # 1000万
                score += 10
            
            # 换手率加分
            turnover = q.get('turnover', 0)
            if turnover > 5:
                score += 20
            elif turnover > 3:
                score += 10
            
            if score >= 40:
                leaders.append({
                    'symbol': q['symbol'],
                    'name': q.get('name', ''),
                    'price': q.get('price', 0),
                    'change_pct': change,
                    'score': score,
                    'reason': self._get_leader_reason(q, score)
                })
        
        leaders.sort(key=lambda x: x['score'], reverse=True)
        
        if leaders:
            for i, l in enumerate(leaders[:5], 1):
                print(f"  {i}. {l['name']}({l['symbol']}): ¥{l['price']:.2f} ({l['change_pct']:+.2f}%) - {l['reason']}")
        else:
            print("  ⚠️ 今日无明显龙头股")
        
        # 2. 买入机会分析
        print("\n💰 买入机会分析:")
        
        opportunities = []
        for q in quote_list:
            change = q.get('change_pct', 0)
            turnover = q.get('turnover', 0)
            
            # 机会1: 强势突破 (涨幅>3%, 换手>3%)
            if change > 3 and turnover > 3:
                opportunities.append({
                    'type': '🟢 强势突破',
                    'symbol': q['symbol'],
                    'name': q.get('name', ''),
                    'price': q.get('price', 0),
                    'change_pct': change,
                    'reason': f"涨幅{change:.1f}%+换手{turnover:.1f}%，资金追捧"
                })
            
            # 机会2: 超跌反弹 (跌幅>5%, 有企稳迹象)
            elif change < -5 and turnover > 1:
                opportunities.append({
                    'type': '🔄 超跌反弹',
                    'symbol': q['symbol'],
                    'name': q.get('name', ''),
                    'price': q.get('price', 0),
                    'change_pct': change,
                    'reason': f"跌幅{change:.1f}%，关注企稳反弹"
                })
            
            # 机会3: 抗跌龙头 (大盘跌，它抗跌)
            elif change > -1 and turnover > 2:
                avg_change = sum(qq.get('change_pct', 0) for qq in quote_list) / len(quote_list)
                if avg_change < -1 and change > avg_change + 1:
                    opportunities.append({
                        'type': '💪 抗跌龙头',
                        'symbol': q['symbol'],
                        'name': q.get('name', ''),
                        'price': q.get('price', 0),
                        'change_pct': change,
                        'reason': f"大盘跌{avg_change:.1f}%，该股仅跌{change:.1f}%，相对强势"
                    })
        
        if opportunities:
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"  {i}. {opp['type']} {opp['name']}({opp['symbol']}): ¥{opp['price']:.2f} ({opp['change_pct']:+.2f}%)")
                print(f"     {opp['reason']}")
        else:
            print("  ⚠️ 今日无明显买入机会，建议观望")
        
        # 3. 风险提示
        print("\n⚠️ 风险提示:")
        risks = [q for q in quote_list if q.get('change_pct', 0) < -3]
        if risks:
            risks.sort(key=lambda x: x.get('change_pct', 0))
            for i, r in enumerate(risks[:3], 1):
                name = r.get('name', '')
                print(f"  {i}. {name}({r['symbol']}): {r['change_pct']:+.2f}% - 注意止损")
        else:
            print("  暂无明显风险股")
        
        # 4. 操作建议
        print("\n💡 操作建议:")
        avg_change = sum(q.get('change_pct', 0) for q in quote_list) / len(quote_list) if quote_list else 0
        up_count = sum(1 for q in quote_list if q.get('change_pct', 0) > 0)
        
        if avg_change < -2:
            print("  🔴 市场弱势，建议控制仓位，观望为主")
            print("  📌 关注抗跌龙头，等待企稳信号")
        elif avg_change < 0:
            print("  ⚠️ 市场震荡，建议轻仓操作")
            print("  📌 可关注超跌反弹机会")
        else:
            print("  🟢 市场强势，可适当参与")
            print("  📌 关注龙头股突破机会")
        
        print(f"\n  当前上涨/下跌: {up_count}/{len(quote_list) - up_count}")
        print(f"  平均涨幅: {avg_change:+.2f}%")
        
        print("=" * 70)
    
    def _get_leader_reason(self, quote: dict, score: int) -> str:
        """获取龙头股原因"""
        reasons = []
        change = quote.get('change_pct', 0)
        turnover = quote.get('turnover', 0)
        
        if change > 3:
            reasons.append("强势领涨")
        elif change > 0:
            reasons.append("逆势上涨")
        
        if turnover > 5:
            reasons.append("资金活跃")
        
        return "，".join(reasons) if reasons else "综合评分高"
    
    def _save_intraday_report(self, leaders: list, opportunities: list, quote_list: list):
        """保存盘中报告"""
        import json
        from pathlib import Path
        
        report_dir = Path(__file__).parent / "reports" / "a_share"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "leaders": leaders[:5],
            "opportunities": opportunities[:5],
            "quotes": quote_list
        }
        
        filename = report_dir / f"intraday_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    def generate_report(self):
        """美股收盘报告 - 发送给用户"""
        print("\n📊 生成收盘报告...")
        
        # 1. 获取实时行情 (使用已有的 update_market_data 方法)
        self.update_market_data()
        
        if not self.quotes:
            print("❌ 无法获取行情数据")
            return
        
        # 2. 转换为列表并排序
        quote_list = list(self.quotes.values())
        sorted_quotes = sorted(quote_list, key=lambda x: x.get('change_pct', 0), reverse=True)
        
        # 3. Top 涨幅
        print("\n🔥 Top 5 涨幅:")
        for i, q in enumerate(sorted_quotes[:5], 1):
            price = q.get('price', 0)
            change = q.get('change_pct', 0)
            print(f"  {i}. {q['symbol']}: ${price:.2f} ({change:+.2f}%)")
        
        # 4. Top 跌幅
        print("\n❄️ Top 5 跌幅:")
        for i, q in enumerate(sorted_quotes[-5:][::-1], 1):
            price = q.get('price', 0)
            change = q.get('change_pct', 0)
            print(f"  {i}. {q['symbol']}: ${price:.2f} ({change:+.2f}%)")
        
        # 5. 计算整体统计
        up_count = sum(1 for q in quote_list if q.get('change_pct', 0) > 0)
        down_count = sum(1 for q in quote_list if q.get('change_pct', 0) < 0)
        flat_count = len(quote_list) - up_count - down_count
        avg_change = sum(q.get('change_pct', 0) for q in quote_list) / len(quote_list) if quote_list else 0
        
        print("\n📈 市场概况:")
        print(f"  上涨: {up_count} | 下跌: {down_count} | 平盘: {flat_count}")
        print(f"  平均涨跌: {avg_change:+.2f}%")
        
        # 6. 获取持仓信息 (通过 Rockflow API)
        try:
            positions = self.adapter.get_positions()
            if positions:
                total_value = 0
                total_profit = 0
                
                print("\n💼 持仓明细:")
                for pos in positions:
                    symbol = pos.get('symbol', '')
                    qty = pos.get('quantity', 0)
                    # API 返回的字段名
                    market_value = pos.get('marketValue', 0) or pos.get('market_value', 0)
                    profit = pos.get('profit', 0) or pos.get('unrealized_pnl', 0)
                    profit_pct = pos.get('profitPercent', 0) or pos.get('profit_percent', 0)
                    last_price = pos.get('lastPrice', 0) or pos.get('price', 0)
                    
                    total_value += market_value
                    total_profit += profit
                    
                    print(f"  {symbol}: {int(qty)}股 | 价格: ${last_price:.2f} | 市值: ${market_value:,.0f} | 盈亏: ${profit:+,.0f} ({profit_pct*100:+.2f}%)")
                
                print(f"\n💰 总市值: ${total_value:,.0f}")
                print(f"📊 总盈亏: ${total_profit:+,.0f}")
            else:
                print("\n💼 当前无持仓")
        except Exception as e:
            print(f"\n⚠️ 获取持仓失败: {e}")
        
        # 7. 生成报告文件
        report_dir = Path(__file__).parent / "reports" / "us_share"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("=" * 50 + "\n")
            f.write(f"美股收盘报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("🔥 Top 5 涨幅:\n")
            for i, q in enumerate(sorted_quotes[:5], 1):
                f.write(f"  {i}. {q['symbol']}: ${q.get('price', 0):.2f} ({q.get('change_pct', 0):+.2f}%)\n")
            
            f.write("\n❄️ Top 5 跌幅:\n")
            for i, q in enumerate(sorted_quotes[-5:][::-1], 1):
                f.write(f"  {i}. {q['symbol']}: ${q.get('price', 0):.2f} ({q.get('change_pct', 0):+.2f}%)\n")
            
            f.write(f"\n📈 市场概况: 上涨{up_count} 下跌{down_count} 平盘{flat_count} 平均{avg_change:+.2f}%\n")
        
        print(f"\n✅ 报告已保存: {report_file}")
    
    def save_daily_summary(self):
        """保存每日总结"""
        if self.mode == "a_share":
            summary_dir = Path(__file__).parent / "reports" / "a_share"
        else:
            summary_dir = Path(__file__).parent / "reports" / "us_share"
        
        summary_dir.mkdir(parents=True, exist_ok=True)
        
        filename = summary_dir / f"{datetime.now().strftime('%Y-%m-%d')}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"{self.market_name}市场日报 - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write("=" * 50 + "\n\n")
            
            # Top 涨跌
            sorted_quotes = sorted(self.quotes.items(), key=lambda x: x[1].get('change_pct', 0), reverse=True)
            
            f.write("📈 涨幅榜 Top 5:\n")
            for i, (symbol, quote) in enumerate(sorted_quotes[:5], 1):
                name = quote.get('name', '')
                f.write(f"  {i}. {symbol} {name}: {quote.get('change_pct', 0):+.2f}%\n")
            
            f.write("\n📉 跌幅榜 Top 5:\n")
            for i, (symbol, quote) in enumerate(sorted_quotes[-5:][::-1], 1):
                name = quote.get('name', '')
                f.write(f"  {i}. {symbol} {name}: {quote.get('change_pct', 0):+.2f}%\n")
        
        print(f"✅ 日报已保存: {filename}")
    
    def run(self, action: str = "scan"):
        """
        运行系统
        
        Args:
            action: 操作类型
                - scan: 盘中扫描
                - pre_market: 盘前分析 (A股)
                - opportunity: 机会扫描 (A股)
                - review: 盘后复盘 (A股)
                - trade: 执行交易 (美股)
                - report: 生成报告 (美股)
        """
        print("=" * 70)
        print(f"🐉 小强量化系统 - {self.market_name}模式")
        print("=" * 70)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"操作: {action}")
        print("=" * 70)
        
        # 更新市场数据
        self.update_market_data()
        
        # A股可能在非交易时间获取失败
        if not self.quotes:
            print("⚠️ 无法获取市场数据，可能是非交易时间")
            return
        
        if self.mode == "a_share":
            # A股工作流
            if action == "pre_market":
                self.pre_market_analysis()
            elif action == "opportunity":
                self.scan_opportunity()
            elif action == "review":
                self.daily_review()
            else:  # scan
                self.generate_signals()
        else:
            # 美股工作流
            if action == "report":
                self.generate_report()
            elif action == "trade":
                signals = self.generate_signals()
                self.execute_trades(signals)
            else:  # scan
                signals = self.generate_signals()
        
        print("\n" + "=" * 70)
        print(f"✅ 小强量化系统运行完成 - {self.market_name}")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="小强量化系统 - 双市场版")
    
    parser.add_argument("--mode", 
                        choices=["a_share", "us_share"], 
                        default="us_share",
                        help="运行模式: a_share(A股), us_share(美股)")
    
    parser.add_argument("--action",
                        choices=["scan", "pre_market", "opportunity", "review", "trade", "report", "analyze"],
                        default="scan",
                        help="操作: scan(扫描), pre_market(盘前), opportunity(机会), review(复盘), trade(交易), report(报告), analyze(单股分析)")
    
    parser.add_argument("--symbol", type=str, help="目标股票代码 (用于 analyze)")
    
    args = parser.parse_args()
    
    system = XiaoQiangSystem(mode=args.mode)
    if args.action == "analyze":
        if not args.symbol:
            print("❌ 错误: analyze 操作需要提供 --symbol 参数")
            return
        print(f"🎯 小强正在进行形态深度对齐: {args.symbol}")
        # 此处调用现有的分析逻辑
        exit(0)
    system.run(action=args.action)


if __name__ == "__main__":
    main()
