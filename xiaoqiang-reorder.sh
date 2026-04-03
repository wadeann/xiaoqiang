#!/bin/bash
# 财神重新下单脚本 - 2026-04-01

cd /home/wade/.openclaw/agents/ceo/workspace

API_KEY="rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
BASE_URL="https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"

echo "=== 财神重新下单 - $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""

# 检查账户
echo "📊 检查账户状态..."
ACCOUNT=$(curl -s -X GET "$BASE_URL/account/info" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  --connect-timeout 10 \
  --max-time 30)

echo "$ACCOUNT" | python3 -m json.tool 2>/dev/null || echo "$ACCOUNT"
echo ""

# 下单 NBIS
echo "📈 下单 NBIS..."
ORDER_NBIS=$(curl -s -X POST "$BASE_URL/order/submit" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NBIS",
    "market": "US",
    "side": "BUY",
    "orderType": "MARKET",
    "quantity": 2899
  }' \
  --connect-timeout 10 \
  --max-time 30)
echo "$ORDER_NBIS" | python3 -m json.tool 2>/dev/null || echo "$ORDER_NBIS"
echo ""

# 下单 CRWV
echo "📈 下单 CRWV..."
ORDER_CRWV=$(curl -s -X POST "$BASE_URL/order/submit" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "CRWV",
    "market": "US",
    "side": "BUY",
    "orderType": "MARKET",
    "quantity": 3881
  }' \
  --connect-timeout 10 \
  --max-time 30)
echo "$ORDER_CRWV" | python3 -m json.tool 2>/dev/null || echo "$ORDER_CRWV"
echo ""

# 下单 ARM
echo "📈 下单 ARM..."
ORDER_ARM=$(curl -s -X POST "$BASE_URL/order/submit" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "ARM",
    "market": "US",
    "side": "BUY",
    "orderType": "MARKET",
    "quantity": 1985
  }' \
  --connect-timeout 10 \
  --max-time 30)
echo "$ORDER_ARM" | python3 -m json.tool 2>/dev/null || echo "$ORDER_ARM"
echo ""

echo "✅ 下单完成"
