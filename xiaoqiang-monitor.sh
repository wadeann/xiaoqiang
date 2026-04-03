#!/bin/bash
# 抓龙计划 - 持续监控脚本

API_KEY="rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
BASE="https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"
LOG_DIR="/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang-logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

echo "=========================================="
echo "抓龙计划 - 监控报告"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 资产
echo ""
echo "📊 账户状态"
echo "------------------------------------------"
ASSETS=$(curl -s "$BASE/assets" -H "X-API-Key: $API_KEY")
echo "$ASSETS" | jq -r '.data.data.broker.account[0] | "总资产: $\(.totalAssets)\n现金: $\(.availableCash.USD)\n购买力: $\(.buyingPower)\n今日盈亏: $\(.todayProfitAndLoss) (\(.todayProfitAndLossRate * 100)%)"'

# 持仓
echo ""
echo "📈 当前持仓"
echo "------------------------------------------"
POSITIONS=$(curl -s "$BASE/positions" -H "X-API-Key: $API_KEY")
POS_COUNT=$(echo "$POSITIONS" | jq '.data.data | length')
if [ "$POS_COUNT" -gt 0 ]; then
    echo "$POSITIONS" | jq -r '.data.data[] | "\(.symbol): \(.quantity)股 @ $\(.)"'
else
    echo "空仓"
fi

# 待成交订单
echo ""
echo "⏳ 待成交订单"
echo "------------------------------------------"
ORDERS=$(curl -s "$BASE/orders?filled=false" -H "X-API-Key: $API_KEY")
ORDER_COUNT=$(echo "$ORDERS" | jq '.data.data | length')
if [ "$ORDER_COUNT" -gt 0 ]; then
    echo "$ORDERS" | jq -r '.data.data[] | "[\(.orderStatus)] \(.side) \(.symbol): \(.quantity)股"'
else
    echo "无"
fi

# 收益率计算
TOTAL=$(echo "$ASSETS" | jq -r '.data.data.broker.account[0].totalAssets')
PNL_RATE=$(echo "scale=4; ($TOTAL - 1000000) / 1000000 * 100" | bc)
echo ""
echo "💰 收益统计"
echo "------------------------------------------"
echo "起始资金: $1,000,000"
echo "当前资产: \$$TOTAL"
echo "收益率: ${PNL_RATE}%"
echo "目标: +100%"
echo "止损: -10%"

# 排行榜
echo ""
echo "🏆 排行榜 Top 5"
echo "------------------------------------------"
curl -s "$BASE/arena/campaign/rank?limit=5" -H "X-API-Key: $API_KEY" | jq -r '.data.data.ranks[:5][] | "#\(.rank) \(.model): \(.currentEarningYieldRate * 100)%"' 2>/dev/null

echo ""
echo "=========================================="
