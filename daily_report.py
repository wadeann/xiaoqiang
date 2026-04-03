#!/usr/bin/env python3
"""
华尔街之狼 - 每日复盘报告
总结经验、吸取教训、持续进化
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import requests

# 配置
API_KEY = "rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
BASE_URL = "https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"

class DailyReporter:
    def __init__(self):
        self.headers = {"X-API-Key": API_KEY}
        self.log_dir = Path("/home/wade/.openclaw/logs")
        self.report_dir = Path("reports")
        self.report_dir.mkdir(exist_ok=True)
        
    def get_positions(self):
        """获取持仓"""
        try:
            resp = requests.get(f"{BASE_URL}/positions", headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", {}).get("data", [])
        except:
            pass
        return []
    
    def get_orders(self):
        """获取订单"""
        try:
            resp = requests.get(f"{BASE_URL}/orders", headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", {}).get("data", [])
        except:
            pass
        return []
    
    def load_watchlist(self):
        """加载观察列表"""
        watchlist_file = Path("watchlist/current.json")
        if watchlist_file.exists():
            with open(watchlist_file, 'r') as f:
                return json.load(f)
        return {"stocks": []}
    
    def load_trading_log(self):
        """加载交易日志"""
        log_file = self.log_dir / "xiaoqiang_trader.log"
        if not log_file.exists():
            return []
        
        trades = []
        with open(log_file, 'r') as f:
            for line in f:
                if "买入" in line or "卖出" in line:
                    trades.append(line.strip())
        return trades
    
    def analyze_performance(self):
        """分析今日表现"""
        positions = self.get_positions()
        watchlist = self.load_watchlist()
        
        # 计算收益
        total_pnl = 0
        total_pnl_pct = 0
        wins = 0
        losses = 0
        
        for pos in positions:
            pnl = pos.get("unrealizedPnl", 0)
            pnl_pct = pos.get("unrealizedPnlRate", 0) * 100
            
            total_pnl += pnl
            total_pnl_pct += pnl_pct
            
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
        
        # 分析观察列表
        watchlist_performance = []
        for stock in watchlist.get("stocks", []):
            change = stock.get("current_change", 0)
            holding_return = stock.get("holding_return", 0)
            days = stock.get("days_in_list", 0)
            
            watchlist_performance.append({
                "symbol": stock.get("symbol"),
                "change": change,
                "return": holding_return,
                "days": days,
            })
        
        return {
            "positions": len(positions),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct / len(positions) if positions else 0,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            "watchlist": watchlist_performance,
        }
    
    def generate_report(self):
        """生成每日复盘报告"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        # 分析表现
        perf = self.analyze_performance()
        
        # 加载交易日志
        trades = self.load_trading_log()
        
        # 生成报告
        report = []
        report.append("=" * 70)
        report.append(f"🐺 华尔街之狼 - 每日复盘报告")
        report.append(f"📅 {date_str} {now.strftime('%H:%M')}")
        report.append("=" * 70)
        
        # 1. 今日交易总结
        report.append("")
        report.append("📊 今日交易总结")
        report.append("-" * 70)
        if trades:
            today_trades = [t for t in trades if date_str in t]
            if today_trades:
                for trade in today_trades[-10:]:  # 最近10条
                    report.append(f"  {trade}")
            else:
                report.append("  今日无交易")
        else:
            report.append("  暂无交易记录")
        
        # 2. 持仓表现
        report.append("")
        report.append("💼 持仓表现")
        report.append("-" * 70)
        report.append(f"  持仓数量: {perf['positions']}")
        report.append(f"  总收益: ${perf['total_pnl']:,.2f} ({perf['total_pnl_pct']:+.2f}%)")
        report.append(f"  盈利: {perf['wins']} 只 | 亏损: {perf['losses']} 只")
        report.append(f"  胜率: {perf['win_rate']:.1f}%")
        
        # 3. 观察列表表现
        report.append("")
        report.append("📋 观察列表表现")
        report.append("-" * 70)
        for stock in perf["watchlist"][:5]:
            symbol = stock["symbol"]
            change = stock["change"]
            ret = stock["return"]
            days = stock["days"]
            
            emoji = "🔥" if change >= 10 else "📈" if change >= 5 else "📊"
            ret_emoji = "🟢" if ret >= 0 else "🔴"
            
            report.append(f"  {emoji} {symbol}: {change:+.2f}% | 收益: {ret_emoji} {ret:+.2f}% | {days}天")
        
        # 4. 经验教训
        report.append("")
        report.append("💡 经验教训")
        report.append("-" * 70)
        
        lessons = []
        
        if perf["win_rate"] >= 70:
            lessons.append("  ✅ 胜率较高，选股策略有效")
        elif perf["win_rate"] < 50:
            lessons.append("  ❌ 胜率较低，需要提高选股门槛")
        
        if perf["total_pnl_pct"] > 5:
            lessons.append("  ✅ 收益良好，保持当前策略")
        elif perf["total_pnl_pct"] < -5:
            lessons.append("  ❌ 亏损较大，需要加强风控")
        
        # 检查观察列表中的表现
        for stock in perf["watchlist"]:
            if stock["return"] < -5:
                lessons.append(f"  ⚠️ {stock['symbol']} 收益 {stock['return']:.2f}%，考虑止损")
            elif stock["return"] > 10:
                lessons.append(f"  🎯 {stock['symbol']} 收益 {stock['return']:.2f}%，考虑止盈")
        
        if lessons:
            for lesson in lessons[:5]:
                report.append(lesson)
        else:
            report.append("  暂无明显经验教训")
        
        # 5. 明日计划
        report.append("")
        report.append("📅 明日计划")
        report.append("-" * 70)
        
        # 读取进化后的规则
        rules_file = Path("rules.json")
        if rules_file.exists():
            with open(rules_file, 'r') as f:
                rules = json.load(f)
            
            report.append(f"  选股门槛: 涨幅 > {rules.get('min_change_pct', 4.0)}%")
            report.append(f"  止损线: {rules.get('stop_loss_pct', -10.0)}%")
            report.append(f"  止盈线: {rules.get('take_profit_pct', 20.0)}%")
            report.append(f"  最大持仓: {rules.get('max_positions', 3)} 只")
            report.append(f"  单只仓位: {rules.get('position_size', 0.3)*100:.0f}%")
        else:
            report.append("  使用默认规则")
        
        # 6. 总结
        report.append("")
        report.append("=" * 70)
        if perf["total_pnl"] > 0:
            report.append("✅ 今日盈利，策略有效，继续保持")
        elif perf["total_pnl"] < 0:
            report.append("❌ 今日亏损，反思调整，明日再战")
        else:
            report.append("📊 今日持平，观望等待，谨慎操作")
        report.append("=" * 70)
        
        # 打印报告
        print("\n".join(report))
        
        # 保存报告
        report_file = self.report_dir / f"{date_str}.txt"
        with open(report_file, 'w') as f:
            f.write("\n".join(report))
        
        # 更新历史记录
        history_file = Path("history/daily_summary.json")
        history_file.parent.mkdir(exist_ok=True)
        
        history = []
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        history.append({
            "date": date_str,
            "positions": perf["positions"],
            "total_pnl": perf["total_pnl"],
            "total_pnl_pct": perf["total_pnl_pct"],
            "wins": perf["wins"],
            "losses": perf["losses"],
            "win_rate": perf["win_rate"],
            "watchlist_count": len(perf["watchlist"]),
        })
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        return report

if __name__ == "__main__":
    reporter = DailyReporter()
    reporter.generate_report()
