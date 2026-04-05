import json
from brain import xiaoqiang_scan_logic

def run_synergy_test():
    print("🧪 [协同测试] 开始...")
    symbol = "sh688205"
    raw_change = 0.20
    with open("/home/wade/.openclaw/qlib_evolution/shared/xiaoqiang_orders.json", "r") as f:
        orders = json.load(f)
    qlib_score = orders["top_candidates"].get(symbol, -1.0)
    print(f"📡 {symbol} 涨幅: {raw_change*100:.1f}%, Qlib: {qlib_score:.4f}")
    qlib_pass = xiaoqiang_scan_logic(symbol, raw_change)
    if not qlib_pass:
        print(f"⛔ Qlib 拦截。")
        if raw_change > 0.10:
            print(f"⚡ 启动 LLM 协同分析...")
            from llm_analyst import llm_final_verdict
            verdict = llm_final_verdict(symbol, raw_change, qlib_score)
            print(f"🤖 LLM 研判结果: {verdict}")
            if "[CONFIRM_BUY]" in verdict:
                print(f"✅ [最终决策] 协同通过！LLM 救回了 {symbol}。")
                return True
    return False

if __name__ == "__main__":
    run_synergy_test()