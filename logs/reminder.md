# 抓龙计划 - 重新下单提醒

**执行时间**: 今晚 21:30 (北京时间)
**美股开盘**: 21:30

## 执行方式

### 方式 1: 手动执行
```bash
cd /home/wade/.openclaw/agents/ceo/workspace
./caishen-reorder.sh
```

### 方式 2: 定时任务
```bash
# 添加 crontab (今晚 21:30 执行)
(crontab -l 2>/dev/null; echo "30 21 1 4 * cd /home/wade/.openclaw/agents/ceo/workspace && ./caishen-reorder.sh") | crontab -
```

### 方式 3: 小强监控自动执行
小强持续监控会在美股开盘后自动检测并提示重新下单。

## 目标标的

| 标的 | 仓位 | 当前涨幅 |
|------|------|----------|
| NBIS | $300K | +12.46% |
| CRWV | $300K | +12.03% |
| ARM | $300K | +10.46% |

## 风控

- 止损: -10%
- 目标: +100%
- 监控: 每60秒刷新
