# 抓龙计划 - 重新下单计划

**时间**: 2026-04-01 10:14
**状态**: 订单已取消，等待重新下单

---

## 当前状态

| 项目 | 数值 |
|------|------|
| 总资产 | $1,000,002 |
| 可用现金 | $1,000,002 |
| 购买力 | $2,000,004 |
| 持仓 | 0 |
| 待成交订单 | 0 |

---

## 订单取消原因

**所有订单状态**: `ORDER_CANCELLED`

**可能原因**:
1. 市价单只在正盘时段有效
2. 盘后时段无法成交，系统自动取消
3. 需要在正盘时段重新下单

---

## 重新下单计划

### 执行时间
- **北京时间**: 今晚 21:30
- **美东时间**: 今晚 09:30
- **美股开盘**: 立即执行

### 目标标的

| 标的 | 当前涨幅 | 建议仓位 |
|------|----------|----------|
| **NBIS** | +12.46% 🔥 | 30% ($300K) |
| **CRWV** | +12.03% 🔥 | 30% ($300K) |
| **ARM** | +10.46% 🔥 | 30% ($300K) |
| **NVDA** | +5.59% 📈 | 备选 |
| **TSLA** | +4.64% 📈 | 备选 |

### 订单类型
- **类型**: 市价单 (MARKET_ORDER)
- **时段**: 正盘时段 (TRADING_SESSION)
- **有效期**: 当日有效 (GOOD_FOR_DAY)

---

## 执行脚本

```bash
# 今晚 21:30 执行
cd /home/wade/.openclaw/agents/ceo/workspace
source caishen-logs/.env 2>/dev/null || true

API_KEY="rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
BASE="https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"

# 获取最新价格
NBIS_PRICE=$(curl -s "$BASE/market/tick/latest?market=US&symbol=NBIS" -H "X-API-Key: $API_KEY" | jq -r '.data.data.tradePrice')
CRWV_PRICE=$(curl -s "$BASE/market/tick/latest?market=US&symbol=CRWV" -H "X-API-Key: $API_KEY" | jq -r '.data.data.tradePrice')
ARM_PRICE=$(curl -s "$BASE/market/tick/latest?market=US&symbol=ARM" -H "X-API-Key: $API_KEY" | jq -r '.data.data.tradePrice')

# 下单 NBIS (约 300K)
NBIS_QTY=$(echo "300000 / $NBIS_PRICE" | bc | cut -d. -f1)
curl -X POST "$BASE/orders" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"market\":\"US\",\"symbol\":\"NBIS\",\"instrument\":\"STOCK\",\"orderType\":\"MARKET_ORDER\",\"quantity\":$NBIS_QTY,\"side\":\"BUY\",\"validity\":\"GOOD_FOR_DAY\",\"session\":\"TRADING_SESSION\"}"

# 下单 CRWV (约 300K)
CRWV_QTY=$(echo "300000 / $CRWV_PRICE" | bc | cut -d. -f1)
curl -X POST "$BASE/orders" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"market\":\"US\",\"symbol\":\"CRWV\",\"instrument\":\"STOCK\",\"orderType\":\"MARKET_ORDER\",\"quantity\":$CRWV_QTY,\"side\":\"BUY\",\"validity\":\"GOOD_FOR_DAY\",\"session\":\"TRADING_SESSION\"}"

# 下单 ARM (约 300K)
ARM_QTY=$(echo "300000 / $ARM_PRICE" | bc | cut -d. -f1)
curl -X POST "$BASE/orders" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"market\":\"US\",\"symbol\":\"ARM\",\"instrument\":\"STOCK\",\"orderType\":\"MARKET_ORDER\",\"quantity\":$ARM_QTY,\"side\":\"BUY\",\"validity\":\"GOOD_FOR_DAY\",\"session\":\"TRADING_SESSION\"}"
```

---

## 自动执行

已创建自动执行脚本 `caishen-reorder.sh`，将在今晚 21:30 自动执行。

---

## 风控提醒

- **止损线**: -10% (亏损 $100K 自动清仓)
- **目标收益**: +100%
- **监控频率**: 每 60 秒刷新
- **异常处理**: 如订单再次取消，立即通知 Wade

---

*创建时间: 2026-04-01 10:14*
