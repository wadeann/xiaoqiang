#!/usr/bin/env python3
"""
小强自我进化模块
- 分析历史数据
- 优化选股规则
- 学习成功/失败案例
- 自动调整参数
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import statistics

# 配置
WATCHLIST_DIR = Path("watchlist")
HISTORY_DIR = Path("history")
RULES_FILE = Path("rules.json")
EVOLUTION_LOG = Path("evolution_log.json")

def load_rules():
    """加载当前规则"""
    if RULES_FILE.exists():
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    return {
        "min_change_pct": 3.0,
        "max_change_pct": 50.0,
        "min_volume": 1000000,
        "max_days_hold": 5,
        "stop_loss_pct": -10.0,
        "take_profit_pct": 20.0,
        "version": 1,
        "last_update": None,
    }

def save_rules(rules):
    """保存规则"""
    rules["last_update"] = datetime.now().isoformat()
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)

def load_history(days=30):
    """加载历史数据"""
    history = {"removed": [], "added": []}
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        history_file = HISTORY_DIR / f"{date}.json"
        
        if history_file.exists():
            with open(history_file, 'r') as f:
                data = json.load(f)
                history["removed"].extend(data.get("removed", []))
                history["added"].extend(data.get("added", []))
    
    return history

def analyze_removed():
    """分析被剔除的标的"""
    history = load_history()
    removed = history["removed"]
    
    if not removed:
        return None
    
    # 按剔除原因分组
    reasons = {}
    for item in removed:
        reason = item.get("remove_reason", "unknown")
        if reason not in reasons:
            reasons[reason] = []
        reasons[reason].append(item)
    
    # 计算统计数据
    stats = {
        "total": len(removed),
        "avg_days": statistics.mean([item.get("days_in_list", 0) for item in removed]),
        "avg_return": statistics.mean([item.get("holding_return", 0) for item in removed]),
        "reasons": {r: len(items) for r, items in reasons.items()},
    }
    
    # 识别主要问题
    problems = []
    if stats["avg_return"] < -5:
        problems.append("止损触发频繁，考虑调整止损线")
    if stats["avg_days"] >= 4:
        problems.append("持有时间过长，考虑缩短最大持有天数")
    
    # 找出表现差的标的
    poor_performers = [item for item in removed if item.get("holding_return", 0) < -5]
    if poor_performers:
        stats["poor_performers"] = [(p["symbol"], p.get("holding_return", 0)) for p in poor_performers[:5]]
    
    return stats

def analyze_added():
    """分析新增的标的"""
    history = load_history()
    added = history["added"]
    
    if not added:
        return None
    
    # 按涨幅分组
    changes = [item.get("add_change", 0) for item in added if item.get("add_change")]
    
    if not changes:
        return None
    
    stats = {
        "total": len(added),
        "avg_change": statistics.mean(changes),
        "max_change": max(changes),
        "min_change": min(changes),
        "median_change": statistics.median(changes),
    }
    
    # 识别涨幅分布
    high_performers = len([c for c in changes if c >= 10])
    mid_performers = len([c for c in changes if 5 <= c < 10])
    low_performers = len([c for c in changes if c < 5])
    
    stats["distribution"] = {
        "high (>10%)": high_performers,
        "mid (5-10%)": mid_performers,
        "low (<5%)": low_performers,
    }
    
    return stats

def calculate_win_rate():
    """计算胜率"""
    history = load_history()
    removed = history["removed"]
    
    if not removed:
        return None
    
    wins = len([item for item in removed if item.get("holding_return", 0) > 0])
    losses = len([item for item in removed if item.get("holding_return", 0) <= 0])
    total = wins + losses
    
    if total == 0:
        return None
    
    return {
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / total) * 100,
        "avg_win": statistics.mean([item.get("holding_return", 0) for item in removed if item.get("holding_return", 0) > 0]) if wins > 0 else 0,
        "avg_loss": statistics.mean([item.get("holding_return", 0) for item in removed if item.get("holding_return", 0) <= 0]) if losses > 0 else 0,
    }

def suggest_rule_changes():
    """建议规则调整"""
    rules = load_rules()
    suggestions = []
    
    # 分析被剔除的标的
    removed_stats = analyze_removed()
    if removed_stats:
        # 止损频繁触发
        stop_loss_count = removed_stats.get("reasons", {}).get("止损", 0)
        if stop_loss_count > 3:
            suggestions.append({
                "rule": "stop_loss_pct",
                "current": rules["stop_loss_pct"],
                "suggested": rules["stop_loss_pct"] - 2.0,
                "reason": f"止损触发 {stop_loss_count} 次，建议放宽止损线",
            })
        
        # 持有时间过长
        max_days_count = removed_stats.get("reasons", {}).get("持有天数超限", 0)
        if max_days_count > 2:
            suggestions.append({
                "rule": "max_days_hold",
                "current": rules["max_days_hold"],
                "suggested": rules["max_days_hold"] + 1,
                "reason": f"持有天数超限 {max_days_count} 次，建议延长持有期",
            })
    
    # 分析新增的标的
    added_stats = analyze_added()
    if added_stats:
        # 如果大部分新增标的涨幅较低
        low_performers = added_stats.get("distribution", {}).get("low (<5%)", 0)
        total = added_stats.get("total", 0)
        if total > 0 and low_performers / total > 0.5:
            suggestions.append({
                "rule": "min_change_pct",
                "current": rules["min_change_pct"],
                "suggested": rules["min_change_pct"] + 0.5,
                "reason": f"低涨幅标的占比过高 ({low_performers}/{total})，建议提高涨幅阈值",
            })
    
    # 计算胜率
    win_rate = calculate_win_rate()
    if win_rate:
        if win_rate["win_rate"] < 40:
            suggestions.append({
                "rule": "min_change_pct",
                "current": rules["min_change_pct"],
                "suggested": rules["min_change_pct"] + 1.0,
                "reason": f"胜率过低 ({win_rate['win_rate']:.1f}%)，建议提高选股门槛",
            })
        elif win_rate["win_rate"] > 70:
            suggestions.append({
                "rule": "min_change_pct",
                "current": rules["min_change_pct"],
                "suggested": max(2.0, rules["min_change_pct"] - 0.5),
                "reason": f"胜率较高 ({win_rate['win_rate']:.1f}%)，可尝试降低门槛增加机会",
            })
    
    return suggestions

def apply_suggestions(suggestions, auto=False):
    """应用规则建议"""
    if not suggestions:
        return None
    
    rules = load_rules()
    changes = []
    
    for suggestion in suggestions:
        rule = suggestion["rule"]
        current = suggestion["current"]
        suggested = suggestion["suggested"]
        
        # 验证建议值
        if rule in ["min_change_pct", "max_change_pct"]:
            if suggested < 0 or suggested > 100:
                continue
        elif rule in ["stop_loss_pct", "take_profit_pct"]:
            if suggested < -50 or suggested > 100:
                continue
        elif rule in ["max_days_hold"]:
            if suggested < 1 or suggested > 30:
                continue
        
        # 应用建议
        if auto or True:  # 暂时自动应用
            rules[rule] = suggested
            rules["version"] = rules.get("version", 1) + 1
            changes.append({
                "rule": rule,
                "from": current,
                "to": suggested,
                "reason": suggestion["reason"],
            })
    
    if changes:
        save_rules(rules)
        
        # 记录进化日志
        log_evolution(changes)
    
    return changes

def log_evolution(changes):
    """记录进化日志"""
    log = []
    if EVOLUTION_LOG.exists():
        with open(EVOLUTION_LOG, 'r') as f:
            log = json.load(f)
    
    log.append({
        "timestamp": datetime.now().isoformat(),
        "changes": changes,
    })
    
    with open(EVOLUTION_LOG, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

def evolve():
    """执行自我进化"""
    print("\n" + "="*70)
    print("🧬 小强自我进化系统")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    # 1. 分析历史数据
    print("\n📊 分析历史数据...")
    
    removed_stats = analyze_removed()
    if removed_stats:
        print(f"\n剔除标的分析:")
        print(f"  总数: {removed_stats['total']}")
        print(f"  平均持有天数: {removed_stats['avg_days']:.1f}")
        print(f"  平均收益: {removed_stats['avg_return']:.2f}%")
        print(f"  剔除原因分布: {removed_stats['reasons']}")
    else:
        print("\n无剔除历史数据")
    
    added_stats = analyze_added()
    if added_stats:
        print(f"\n新增标的分析:")
        print(f"  总数: {added_stats['total']}")
        print(f"  平均涨幅: {added_stats['avg_change']:.2f}%")
        print(f"  涨幅分布: {added_stats['distribution']}")
    else:
        print("\n无新增历史数据")
    
    win_rate = calculate_win_rate()
    if win_rate:
        print(f"\n胜率分析:")
        print(f"  胜: {win_rate['wins']} | 负: {win_rate['losses']}")
        print(f"  胜率: {win_rate['win_rate']:.1f}%")
        print(f"  平均盈利: {win_rate['avg_win']:.2f}%")
        print(f"  平均亏损: {win_rate['avg_loss']:.2f}%")
    
    # 2. 生成建议
    print("\n" + "-"*70)
    print("💡 规则优化建议")
    print("-"*70)
    
    suggestions = suggest_rule_changes()
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n{i}. {suggestion['rule']}")
            print(f"   当前: {suggestion['current']}")
            print(f"   建议: {suggestion['suggested']}")
            print(f"   原因: {suggestion['reason']}")
    else:
        print("\n暂无优化建议")
    
    # 3. 应用建议
    if suggestions:
        print("\n" + "-"*70)
        print("🔄 应用规则调整")
        print("-"*70)
        
        changes = apply_suggestions(suggestions, auto=True)
        if changes:
            for change in changes:
                print(f"\n✅ {change['rule']}: {change['from']} → {change['to']}")
                print(f"   原因: {change['reason']}")
        else:
            print("\n无有效调整")
    
    # 4. 显示当前规则
    rules = load_rules()
    print("\n" + "-"*70)
    print(f"📋 当前规则 (v{rules.get('version', 1)})")
    print("-"*70)
    for key, value in rules.items():
        if key not in ["version", "last_update"]:
            print(f"  {key}: {value}")
    
    print("\n" + "="*70)
    print("✅ 自我进化完成")
    print("="*70 + "\n")
    
    return {
        "removed_stats": removed_stats,
        "added_stats": added_stats,
        "win_rate": win_rate,
        "suggestions": suggestions,
        "changes": changes if suggestions else [],
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="小强自我进化模块")
    parser.add_argument("--evolve", action="store_true", help="执行自我进化")
    parser.add_argument("--stats", action="store_true", help="显示统计数据")
    parser.add_argument("--rules", action="store_true", help="显示当前规则")
    
    args = parser.parse_args()
    
    if args.evolve:
        evolve()
    elif args.stats:
        removed = analyze_removed()
        added = analyze_added()
        win = calculate_win_rate()
        
        print("\n📊 统计数据")
        print("-"*70)
        print(f"剔除分析: {removed}")
        print(f"新增分析: {added}")
        print(f"胜率分析: {win}")
    elif args.rules:
        rules = load_rules()
        print("\n📋 当前规则")
        print("-"*70)
        for key, value in rules.items():
            print(f"  {key}: {value}")
    else:
        evolve()

if __name__ == "__main__":
    main()
