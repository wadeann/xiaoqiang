#!/usr/bin/env python3
"""
小强自我进化模块 v2.0
- 分析历史预测准确率
- 分析持仓表现
- 优化选股规则
- 基于回测结果进化
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
PREDICTIONS_FILE = Path("history/predictions.json")


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
        "trailing_stop_pct": 5.0,
        "version": 1,
        "last_update": None,
        "win_rate_history": [],
    }


def save_rules(rules):
    """保存规则"""
    rules["last_update"] = datetime.now().isoformat()
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)


def load_predictions():
    """加载预测记录"""
    if PREDICTIONS_FILE.exists():
        with open(PREDICTIONS_FILE, 'r') as f:
            return json.load(f)
    return {"records": []}


def analyze_predictions():
    """分析预测准确率"""
    predictions = load_predictions()
    records = predictions.get("records", [])
    
    if not records:
        return None
    
    # 统计预测准确率
    verified_records = []
    pending = 0
    
    for record in records:
        if record.get("actual") is None:
            pending += 1
        else:
            verified_records.append(record)
    
    total = len(verified_records)
    
    if total == 0:
        return None
    
    correct = 0
    wrong = 0
    
    # 按预测类型分组
    by_prediction = {
        "continue_up": {"total": 0, "correct": 0, "avg_actual": []},
        "continue_down": {"total": 0, "correct": 0, "avg_actual": []},
        "rebound": {"total": 0, "correct": 0, "avg_actual": []},
        "sideways": {"total": 0, "correct": 0, "avg_actual": []},
    }
    
    for record in verified_records:
        prediction = record.get("prediction", "unknown")
        actual = record.get("actual", 0)
        open_change = record.get("open_change", 0)
        
        # 判断预测是否正确
        is_correct = False
        if prediction == "continue_up" and actual > 1:
            is_correct = True
            correct += 1
        elif prediction == "continue_down" and actual < -1:
            is_correct = True
            correct += 1
        elif prediction == "rebound" and actual > 0 and open_change < -2:
            is_correct = True
            correct += 1
        elif prediction == "sideways" and abs(actual) <= 2:
            is_correct = True
            correct += 1
        else:
            wrong += 1
        
        # 按类型统计
        if prediction in by_prediction:
            by_prediction[prediction]["total"] += 1
            by_prediction[prediction]["avg_actual"].append(actual)
            if is_correct:
                by_prediction[prediction]["correct"] += 1
    
    # 计算各类型准确率
    for pred_type in by_prediction:
        if by_prediction[pred_type]["total"] > 0:
            by_prediction[pred_type]["accuracy"] = (
                by_prediction[pred_type]["correct"] / by_prediction[pred_type]["total"] * 100
            )
            if by_prediction[pred_type]["avg_actual"]:
                by_prediction[pred_type]["avg_actual"] = statistics.mean(by_prediction[pred_type]["avg_actual"])
            else:
                by_prediction[pred_type]["avg_actual"] = 0
        else:
            by_prediction[pred_type]["accuracy"] = 0
    
    return {
        "total_verified": total,
        "correct": correct,
        "wrong": wrong,
        "pending": pending,
        "win_rate": (correct / total * 100) if total > 0 else 0,
        "by_prediction": by_prediction,
    }


def analyze_trade_history():
    """分析交易历史"""
    history_files = list(HISTORY_DIR.glob("*.json"))
    """分析交易历史"""
    history_files = list(HISTORY_DIR.glob("*.json"))
    
    all_removed = []
    all_added = []
    
    for f in history_files:
        if f.name in ["predictions.json", "daily_summary.json"]:
            continue
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
                all_removed.extend(data.get("removed", []))
                all_added.extend(data.get("added", []))
        except:
            continue
    
    # 分析被剔除的标的
    removed_stats = None
    if all_removed:
        returns = [r.get("holding_return", 0) for r in all_removed if r.get("holding_return") is not None]
        days = [r.get("days_in_list", 0) for r in all_removed]
        
        wins = len([r for r in returns if r > 0])
        losses = len([r for r in returns if r <= 0])
        
        removed_stats = {
            "total": len(all_removed),
            "avg_return": statistics.mean(returns) if returns else 0,
            "avg_days": statistics.mean(days) if days else 0,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(returns) * 100) if returns else 0,
        }
    
    # 分析新增的标的
    added_stats = None
    if all_added:
        changes = [a.get("add_change", 0) for a in all_added if a.get("add_change") is not None]
        
        added_stats = {
            "total": len(all_added),
            "avg_change": statistics.mean(changes) if changes else 0,
            "max_change": max(changes) if changes else 0,
            "min_change": min(changes) if changes else 0,
        }
    
    return {
        "removed": removed_stats,
        "added": added_stats,
    }


def suggest_rule_changes(predictions_stats, trade_stats):
    """基于统计数据建议规则调整"""
    rules = load_rules()
    suggestions = []
    
    # 基于预测准确率
    if predictions_stats:
        win_rate = predictions_stats.get("win_rate", 0)
        
        # 胜率低于 40%，提高门槛
        if win_rate < 40:
            suggestions.append({
                "rule": "min_change_pct",
                "current": rules["min_change_pct"],
                "suggested": min(rules["min_change_pct"] + 1.0, 10.0),
                "reason": f"预测胜率过低 ({win_rate:.1f}%)，建议提高涨幅阈值",
                "priority": "high",
            })
        
        # 胜率高于 60%，可以降低门槛
        elif win_rate > 60:
            suggestions.append({
                "rule": "min_change_pct",
                "current": rules["min_change_pct"],
                "suggested": max(rules["min_change_pct"] - 0.5, 2.0),
                "reason": f"预测胜率良好 ({win_rate:.1f}%)，可尝试降低门槛增加机会",
                "priority": "low",
            })
        
        # 分析各预测类型表现
        by_pred = predictions_stats.get("by_prediction", {})
        for pred_type, stats in by_pred.items():
            if stats["total"] >= 5:  # 至少 5 次预测才统计
                if stats["accuracy"] < 30:
                    suggestions.append({
                        "rule": f"disable_{pred_type}",
                        "current": "enabled",
                        "suggested": "disabled",
                        "reason": f"{pred_type} 预测准确率过低 ({stats['accuracy']:.1f}%)",
                        "priority": "medium",
                    })
    
    # 基于交易历史
    if trade_stats:
        removed = trade_stats.get("removed")
        if removed:
            # 止损频繁
            if removed["losses"] > removed["wins"] * 2:
                suggestions.append({
                    "rule": "stop_loss_pct",
                    "current": rules["stop_loss_pct"],
                    "suggested": rules["stop_loss_pct"] - 2.0,
                    "reason": f"亏损次数 ({removed['losses']}) 远多于盈利 ({removed['wins']})，建议放宽止损线",
                    "priority": "high",
                })
            
            # 平均收益为负
            if removed["avg_return"] < -3:
                suggestions.append({
                    "rule": "min_change_pct",
                    "current": rules["min_change_pct"],
                    "suggested": rules["min_change_pct"] + 0.5,
                    "reason": f"平均收益为负 ({removed['avg_return']:.2f}%)，建议提高选股门槛",
                    "priority": "high",
                })
    
    # 按优先级排序
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda x: priority_order.get(x["priority"], 99))
    
    return suggestions


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


def apply_suggestions(suggestions, auto=True):
    """应用规则建议"""
    if not suggestions:
        return []
    
    rules = load_rules()
    changes = []
    
    for suggestion in suggestions:
        rule = suggestion["rule"]
        current = suggestion["current"]
        suggested = suggestion["suggested"]
        
        # 跳过禁用类型的建议
        if rule.startswith("disable_"):
            continue
        
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
        if auto:
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
        log_evolution(changes)
    
    return changes


def evolve():
    """执行自我进化"""
    print("\n" + "=" * 70)
    print("🧬 小强自我进化系统 v2.0")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # 1. 分析预测准确率
    print("\n📊 预测准确率分析...")
    predictions_stats = analyze_predictions()
    
    if predictions_stats:
        print(f"\n  已验证预测: {predictions_stats['total_verified']} 条")
        print(f"  正确: {predictions_stats['correct']} | 错误: {predictions_stats['wrong']} | 待验证: {predictions_stats['pending']}")
        print(f"  总体胜率: {predictions_stats['win_rate']:.1f}%")
        
        print("\n  各类型预测表现:")
        for pred_type, stats in predictions_stats["by_prediction"].items():
            if stats["total"] > 0:
                print(f"    {pred_type}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1f}%)")
    else:
        print("\n  ⚠️ 无预测数据")
    
    # 2. 分析交易历史
    print("\n📈 交易历史分析...")
    trade_stats = analyze_trade_history()
    
    if trade_stats["removed"]:
        r = trade_stats["removed"]
        print(f"\n  剔除标的: {r['total']} 只")
        print(f"  平均收益: {r['avg_return']:.2f}%")
        print(f"  平均持有: {r['avg_days']:.1f} 天")
        print(f"  盈亏比: {r['wins']}胜 / {r['losses']}负 (胜率 {r['win_rate']:.1f}%)")
    else:
        print("\n  ⚠️ 无交易历史")
    
    if trade_stats["added"]:
        a = trade_stats["added"]
        print(f"\n  新增标的: {a['total']} 只")
        print(f"  平均涨幅: {a['avg_change']:.2f}%")
        print(f"  最高涨幅: {a['max_change']:.2f}%")
        print(f"  最低涨幅: {a['min_change']:.2f}%")
    
    # 3. 生成建议
    print("\n" + "-" * 70)
    print("💡 规则优化建议")
    print("-" * 70)
    
    suggestions = suggest_rule_changes(predictions_stats, trade_stats)
    
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(suggestion["priority"], "⚪")
            print(f"\n{i}. {priority_emoji} {suggestion['rule']}")
            print(f"   当前: {suggestion['current']}")
            print(f"   建议: {suggestion['suggested']}")
            print(f"   原因: {suggestion['reason']}")
    else:
        print("\n  ✅ 当前规则表现良好，无需调整")
    
    # 4. 应用建议
    changes = []
    if suggestions:
        print("\n" + "-" * 70)
        print("🔄 应用规则调整")
        print("-" * 70)
        
        changes = apply_suggestions(suggestions, auto=True)
        
        if changes:
            for change in changes:
                print(f"\n  ✅ {change['rule']}: {change['from']} → {change['to']}")
                print(f"     原因: {change['reason']}")
        else:
            print("\n  无有效调整")
    
    # 5. 显示当前规则
    rules = load_rules()
    print("\n" + "-" * 70)
    print(f"📋 当前规则 (v{rules.get('version', 1)})")
    print("-" * 70)
    for key, value in rules.items():
        if key not in ["version", "last_update", "win_rate_history"]:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("✅ 自我进化完成")
    print("=" * 70 + "\n")
    
    return {
        "predictions_stats": predictions_stats,
        "trade_stats": trade_stats,
        "suggestions": suggestions,
        "changes": changes,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="小强自我进化模块 v2.0")
    parser.add_argument("--evolve", action="store_true", help="执行自我进化")
    parser.add_argument("--stats", action="store_true", help="显示统计数据")
    parser.add_argument("--rules", action="store_true", help="显示当前规则")
    
    args = parser.parse_args()
    
    if args.stats:
        pred = analyze_predictions()
        trade = analyze_trade_history()
        
        print("\n📊 统计数据")
        print("-" * 70)
        print(f"预测分析: {pred}")
        print(f"交易分析: {trade}")
    elif args.rules:
        rules = load_rules()
        print("\n📋 当前规则")
        print("-" * 70)
        for key, value in rules.items():
            print(f"  {key}: {value}")
    else:
        evolve()
