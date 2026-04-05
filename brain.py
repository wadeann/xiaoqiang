import json
from pathlib import Path

def xiaoqiang_scan_logic(stock_code, raw_price_change):
    """
    进化版小强决策逻辑：形态过滤器 + AI 过滤器 + 动态阈值
    """
    orders_file = Path("/home/wade/.openclaw/qlib_evolution/shared/xiaoqiang_orders.json")
    scores_file = Path("/home/wade/.openclaw/qlib_evolution/shared/latest_scores.json")
    
    if not orders_file.exists():
        print("警告: 未收到智库指令，使用降级逻辑运行。")
        return raw_price_change > 0.03 # 降级为旧逻辑
    
    with open(orders_file, "r") as f:
        brain_orders = json.load(f)
    
    # 读取最新的评分数据（包含动态阈值信息）
    latest_scores_data = {}
    if scores_file.exists():
        with open(scores_file, "r") as f:
            latest_scores_data = json.load(f)
    
    qlib_scores = brain_orders.get("top_candidates", {})
    base_threshold = brain_orders.get("active_threshold", 0.001)
    
    # 获取动态阈值信息
    individual_thresholds = latest_scores_data.get("individual_thresholds", {})
    special_cases = latest_scores_data.get("special_cases", {})
    
    # 获取个性化阈值（如果可用）
    stock_threshold = individual_thresholds.get(stock_code, base_threshold)
    
    # 1. 传统形态过滤 (小强的老本行)
    pattern_match = raw_price_change > 0.02 # 只要形态不错就行，不用非得 3%
    
    # 2. AI 深度过滤 (Qlib 智库的建议)
    ai_score = qlib_scores.get(stock_code, -999)
    
    # 检查特殊情况
    special_case = special_cases.get(stock_code)
    if special_case == "EXTREME_POSITIVE_MISMATCH":
        print(f"🔥 [特殊处理] {stock_code} 检测到极端值不匹配，形态覆盖AI评分")
        ai_confirm = True
    elif special_case in ["KCB_STOCK_LOW_SCORE", "GEM_STOCK_LOW_SCORE"]:
        print(f"⚠️ [特殊处理] {stock_code} 科创板/创业板评分异常，使用宽松阈值")
        stock_threshold = base_threshold * 0.3  # 更宽松的阈值
        ai_confirm = ai_score > stock_threshold
    else:
        ai_confirm = ai_score > stock_threshold
    
    # 3. 动态阈值调整 - 对强势股特殊处理
    if raw_price_change > 0.15:  # 20cm涨停
        print(f"🚀 [动态阈值] {stock_code} 20cm涨停，大幅降低AI阈值要求")
        stock_threshold = base_threshold * 0.1
        ai_confirm = ai_score > stock_threshold
    elif raw_price_change > 0.10:  # 10%以上涨幅
        print(f"⚡ [动态阈值] {stock_code} 强势上涨，降低AI阈值要求")
        stock_threshold = base_threshold * 0.5
        ai_confirm = ai_score > stock_threshold
    
    if pattern_match and ai_confirm:
        print(f"🚀 [协同决策] {stock_code} 命中！形态匹配且 AI 评分 ({ai_score:.4f}) 超过阈值 {stock_threshold:.4f}")
        return True
    elif pattern_match and not ai_confirm:
        print(f"⏳ [协同决策] {stock_code} 虽形态匹配但 AI 评分 ({ai_score:.4f}) 低于阈值 {stock_threshold:.4f}，已拦截。")
        return False
    return False

if __name__ == "__main__":
    # 模拟扫描
    test_stocks = [
        {"code": "sh601988", "change": 0.025},
        {"code": "sz000001", "change": 0.015}
    ]
    for s in test_stocks:
        xiaoqiang_scan_logic(s["code"], s["change"])
