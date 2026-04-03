#!/bin/bash
# 财神系统 - 抓龙行动
# 目标: 100% 收益 | 风控: -10% 淘汰

API_KEY="rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
BASE_URL="https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"

# 美股标的
US_TICKERS="NVDA TSLA ARM ASML PLTR BABA BIDU MU TSM CRWV IREN NBIS"

# 港股标的
HK_TICKERS="00700.HK 09988.HK 09888.HK 00981.HK 02513.HK 06869.HK 00100.HK"

LOG_DIR="/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang-logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 获取账户资产
get_assets() {
    curl -sS "$BASE_URL/assets" -H "X-API-Key: $API_KEY"
}

# 获取持仓
get_positions() {
    curl -sS "$BASE_URL/positions" -H "X-API-Key: $API_KEY"
}

# 获取行情 (美股)
get_quote_us() {
    local symbol=$1
    curl -sS "$BASE_URL/market/tick/latest?market=US&symbol=$symbol" -H "X-API-Key: $API_KEY"
}

# 获取行情 (港股)
get_quote_hk() {
    local symbol=$1
    curl -sS "$BASE_URL/market/tick/latest?market=HK&symbol=$symbol" -H "X-API-Key: $API_KEY"
}

# 获取标的信息
get_quote_info() {
    local market=$1
    local symbol=$2
    curl -sS "$BASE_URL/markets/$market/quotes/$symbol" -H "X-API-Key: $API_KEY"
}

# 获取可交易数量
get_quantities() {
    local symbol=$1
    local market=$2
    local side=$3
    curl -sS "$BASE_URL/quantities?symbol=$symbol&market=$market&side=$side" -H "X-API-Key: $API_KEY"
}

# 下单
place_order() {
    local market=$1
    local symbol=$2
    local side=$3
    local quantity=$4
    local order_type=$5
    local price=$6
    
    if [ "$order_type" = "MARKET_ORDER" ]; then
        curl -sS -X POST "$BASE_URL/orders" \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"market\":\"$market\",\"symbol\":\"$symbol\",\"instrument\":\"STOCK\",\"orderType\":\"$order_type\",\"quantity\":$quantity,\"side\":\"$side\",\"validity\":\"GOOD_FOR_DAY\",\"session\":\"TRADING_SESSION\"}"
    else
        curl -sS -X POST "$BASE_URL/orders" \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"market\":\"$market\",\"symbol\":\"$symbol\",\"instrument\":\"STOCK\",\"orderType\":\"$order_type\",\"quantity\":$quantity,\"price\":$price,\"side\":\"$side\",\"validity\":\"GOOD_FOR_DAY\",\"session\":\"TRADING_SESSION\"}"
    fi
}

# 获取订单列表
get_orders() {
    local filled=$1
    curl -sS "$BASE_URL/orders?filled=$filled&limit=50" -H "X-API-Key: $API_KEY"
}

# 撤销订单
cancel_order() {
    local order_id=$1
    curl -sS -X DELETE "$BASE_URL/orders/$order_id" -H "X-API-Key: $API_KEY"
}

# 获取排行榜
get_rank() {
    curl -sS "$BASE_URL/arena/campaign/rank?limit=50" -H "X-API-Key: $API_KEY"
}

case "$1" in
    assets)
        get_assets | jq .
        ;;
    positions)
        get_positions | jq .
        ;;
    quote)
        if [ -n "$2" ]; then
            if [[ "$2" == *.HK ]]; then
                get_quote_hk "$2" | jq .
            else
                get_quote_us "$2" | jq .
            fi
        else
            echo "Usage: $0 quote <SYMBOL>"
        fi
        ;;
    scan)
        echo "=== 美股行情扫描 ===" | tee "$LOG_DIR/scan_$TIMESTAMP.log"
        for ticker in $US_TICKERS; do
            echo "--- $ticker ---" | tee -a "$LOG_DIR/scan_$TIMESTAMP.log"
            get_quote_us "$ticker" | jq -c '{symbol: .data.symbol, price: .data.last, change: .data.change, changePercent: .data.changePercent, volume: .data.volume}' 2>/dev/null | tee -a "$LOG_DIR/scan_$TIMESTAMP.log"
            sleep 0.5
        done
        echo "" | tee -a "$LOG_DIR/scan_$TIMESTAMP.log"
        echo "=== 港股行情扫描 ===" | tee -a "$LOG_DIR/scan_$TIMESTAMP.log"
        for ticker in $HK_TICKERS; do
            echo "--- $ticker ---" | tee -a "$LOG_DIR/scan_$TIMESTAMP.log"
            get_quote_hk "$ticker" | jq -c '{symbol: .data.symbol, price: .data.last, change: .data.change, changePercent: .data.changePercent}' 2>/dev/null | tee -a "$LOG_DIR/scan_$TIMESTAMP.log"
            sleep 0.5
        done
        ;;
    rank)
        get_rank | jq '.data.data.ranks[:10] | .[] | {rank, model, currentEarningYieldRate}'
        ;;
    orders)
        get_orders "false" | jq .
        ;;
    filled)
        get_orders "true" | jq .
        ;;
    buy)
        if [ -n "$2" ] && [ -n "$3" ] && [ -n "$4" ]; then
            place_order "$2" "$3" "BUY" "$4" "MARKET_ORDER" | jq .
        else
            echo "Usage: $0 buy <MARKET> <SYMBOL> <QUANTITY>"
        fi
        ;;
    sell)
        if [ -n "$2" ] && [ -n "$3" ] && [ -n "$4" ]; then
            place_order "$2" "$3" "SELL" "$4" "MARKET_ORDER" | jq .
        else
            echo "Usage: $0 sell <MARKET> <SYMBOL> <QUANTITY>"
        fi
        ;;
    cancel)
        if [ -n "$2" ]; then
            cancel_order "$2" | jq .
        else
            echo "Usage: $0 cancel <ORDER_ID>"
        fi
        ;;
    info)
        if [ -n "$2" ] && [ -n "$3" ]; then
            get_quote_info "$2" "$3" | jq .
        else
            echo "Usage: $0 info <MARKET> <SYMBOL>"
        fi
        ;;
    qty)
        if [ -n "$2" ] && [ -n "$3" ] && [ -n "$4" ]; then
            get_quantities "$2" "$3" "$4" | jq .
        else
            echo "Usage: $0 qty <SYMBOL> <MARKET> <BUY|SELL>"
        fi
        ;;
    *)
        echo "财神系统 - 抓龙行动"
        echo ""
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  assets              查看账户资产"
        echo "  positions           查看持仓"
        echo "  quote <SYMBOL>      获取实时行情"
        echo "  scan                扫描所有标的行情"
        echo "  rank                查看排行榜 Top 10"
        echo "  orders              查看待成交订单"
        echo "  filled              查看已成交订单"
        echo "  buy <MARKET> <SYMBOL> <QTY>    市价买入"
        echo "  sell <MARKET> <SYMBOL> <QTY>   市价卖出"
        echo "  cancel <ORDER_ID>   撤销订单"
        echo "  info <MARKET> <SYMBOL>  获取标的信息"
        echo "  qty <SYMBOL> <MARKET> <BUY|SELL>  查询可交易数量"
        ;;
esac
