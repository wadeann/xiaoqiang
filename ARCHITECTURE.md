# 小强量化系统 - 架构文档

> 版本: v2.0 (双市场版)  
> 更新时间: 2026-04-02  
> 作者: CEO Agent (Commander Wade)

---

## 一、系统概览

### 1.1 系统定位

**小强量化系统** 是 CEO Agent 的专属量化工具，支持 **A股 + 美股** 双市场，根据时间自动切换。

| 时间段 | 市场 | 模式 | 功能 |
|--------|------|------|------|
| 08:00-15:30 | A股 | 分析模式 | 扫描、信号生成、盘后总结 |
| 21:20-06:00 | 美股 | 交易模式 | 扫描、信号生成、自动交易 |

**与财神V8的关系**:
- 财神V8 是 CFO Agent 的专属工具
- CEO 不使用财神V8
- 小强独立运行，不依赖财神V8

### 1.2 数据源

| 市场 | 数据源 | 说明 |
|------|--------|------|
| A股 | akshare | 免费、实时、无需API Key |
| 美股 | Rockflow API | Paper Trading 账户 |

- ✅ 实时行情扫描 (19只标的: 美股12 + 港股7)
- ✅ 多策略支持 (动量、均值回归、趋势跟踪)
- ✅ 自动风控 (止损、止盈、仓位管理)
- ✅ Rockflow 交易接口 (下单、撤单、持仓查询)
- ✅ qlib 兼容数据格式 (可扩展回测)

---

## 二、qlib 集成说明

### 2.1 qlib 安装位置

```bash
# 小强系统使用的 qlib 环境
路径: /home/wade/.openclaw/agents/ceo/workspace/xiaoqiang/venv/
版本: pyqlib 0.9.7

# 其他 qlib 环境 (未使用)
/home/wade/.openclaw/workspace/qlib_env/
/home/wade/.openclaw/workspace/projects/qlib-trader/venv/
```

### 2.2 qlib 依赖

```python
# requirements.txt
pyqlib==0.9.7
numpy>=2.4.0
pandas>=2.3.0
scikit-learn>=1.5.0
torch>=2.0.0
akshare>=1.18.0
requests>=2.31.0
pyyaml>=6.0
```

### 2.3 qlib 使用方式

**当前状态**: 小强系统 **兼容 qlib 数据格式**，但尚未深度集成 qlib 的回测引擎。

```python
# data/rockflow_adapter.py
def to_qlib_format(self, quote: Dict) -> Dict:
    """转换为 qlib 格式"""
    return {
        "instrument": quote.get("symbol"),
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "open": quote.get("open"),
        "close": quote.get("tradePrice") or quote.get("close"),
        "high": quote.get("high"),
        "low": quote.get("low"),
        "volume": quote.get("volume"),
        "change_pct": quote.get("changePercent", 0)
    }
```

**扩展方向**: 可使用 qlib 的 `D.calendar()`, `D.features()` 等接口进行回测。

---

## 三、系统架构

### 3.1 目录结构

```
xiaoqiang/
├── main.py                    # 主程序入口
├── config.yaml                # 配置文件
├── requirements.txt           # Python 依赖
├── README.md                  # 使用说明
├── ARCHITECTURE.md            # 本文档
│
├── data/                      # 数据层
│   ├── rockflow_adapter.py    # Rockflow API 适配器
│   ├── rockflow_config.py     # API 配置
│   ├── realtime_fetcher.py    # 实时数据获取
│   ├── cache.py               # 数据缓存
│   └── a_share_data.py        # A股数据 (预留)
│
├── strategies/                # 策略层
│   ├── momentum.py            # 动量策略
│   ├── mean_reversion.py      # 均值回归策略
│   ├── trend_following.py     # 趋势跟踪策略
│   └── risk_manager.py        # 风控管理
│
├── executor/                  # 执行层
│   ├── trader.py              # 交易执行器
│   └── signal_filter.py       # 信号过滤器
│
├── monitor/                   # 监控层
│   └── dashboard.py           # 监控看板
│
├── backtest/                  # 回测层 (qlib)
│   └── run_backtest.py        # 回测引擎
│
├── optimizer/                 # 优化层 (预留)
│
├── utils/                     # 工具函数
│
├── logs/                      # 日志文件
│
├── reports/                   # 日报文件
│
├── history/                   # 历史记录
│
└── watchlist/                 # 监控列表
```

### 3.2 模块职责

```
┌─────────────────────────────────────────────────────────────────────┐
│                          main.py (主程序)                            │
│  - XiaoQiangSystem 类                                                │
│  - 协调各模块工作                                                    │
│  - 支持 scan / trade / monitor 三种模式                              │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    数据层      │   │    策略层      │   │    执行层      │
│  data/        │   │  strategies/  │   │  executor/    │
│               │   │               │   │               │
│ - Rockflow    │   │ - Momentum    │   │ - Trader      │
│   Adapter     │──▶│ - MeanRevert  │──▶│ - SignalFilter│
│ - Realtime    │   │ - TrendFollow │   │               │
│ - Cache       │   │ - RiskManager │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                    ┌───────────────┐
                    │    监控层      │
                    │  monitor/     │
                    │               │
                    │ - Dashboard   │
                    │ - Logger      │
                    └───────────────┘
```

---

## 四、数据流与调用流程

### 4.1 完整调用流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        小强量化系统调用流程                           │
└─────────────────────────────────────────────────────────────────────┘

1. 启动 (main.py)
   │
   ▼
2. 初始化组件
   ├── RockflowAdapter (API 连接)
   ├── RealtimeFetcher (数据获取)
   ├── MomentumStrategy (策略)
   ├── RiskManager (风控)
   └── Trader (交易执行)
   │
   ▼
3. 更新市场数据 (update_market_data)
   │
   ├── RealtimeFetcher.scan_all()
   │   ├── 扫描美股: NVDA, TSLA, ARM, ASML, PLTR, MU, TSM, CRWV, IREN, NBIS, BABA, BIDU
   │   └── 扫描港股: 00700.HK, 09988.HK, 09888.HK, 00981.HK, 02513.HK, 06869.HK, 00100.HK
   │
   └── DataCache.save() → data/cache/latest_quotes.json
   │
   ▼
4. 更新账户状态 (update_account)
   │
   ├── RockflowAdapter.get_assets()
   │   └── GET /assets → 总资产、现金、购买力
   │
   ├── RockflowAdapter.get_positions()
   │   └── GET /positions → 当前持仓
   │
   └── RiskManager.update()
       ├── 计算收益
       ├── 检查止损/止盈
       └── 生成风险报告
   │
   ▼
5. 生成交易信号 (generate_signals)
   │
   ├── MomentumStrategy.generate_signals()
   │   ├── 过滤涨幅 >= 3% 的标的
   │   ├── 按涨幅排序
   │   └── 取 Top 3 生成买入信号
   │
   ├── MeanReversionStrategy.generate_signals()
   │   └── 过滤跌幅 <= -3% 的标的
   │
   └── SignalFilter.filter_signals()
       ├── 过滤涨幅 > 20% (防止追高)
       └── 检查资金充足性
   │
   ▼
6. 执行交易 (execute_trades) [仅 trade 模式]
   │
   ├── Trader.get_account()
   │   └── 获取账户信息
   │
   ├── SignalFilter.calculate_position_size()
   │   └── 计算仓位 (单只标的最大 30% 资金)
   │
   └── Trader.place_order()
       └── POST /orders → 下单
   │
   ▼
7. 输出报告
   │
   ├── 风险报告 (RiskManager.get_risk_report)
   ├── 持仓明细
   └── 交易记录
   │
   ▼
8. 完成
```

### 4.2 数据格式转换

```
Rockflow API 原始数据
{
  "symbol": "NVDA",
  "tradePrice": 174.0,
  "open": 170.0,
  "high": 175.0,
  "low": 169.0,
  "volume": 50000000,
  "changePercent": 2.35
}
        │
        ▼ RockflowAdapter.to_qlib_format()
        │
qlib 兼容格式
{
  "instrument": "NVDA",
  "datetime": "2026-04-02 08:00:00",
  "open": 170.0,
  "close": 174.0,
  "high": 175.0,
  "low": 169.0,
  "volume": 50000000,
  "change_pct": 2.35
}
```

---

## 五、策略详解

### 5.1 动量策略 (Momentum Strategy)

**逻辑**: 追涨强势股，买入当日涨幅最大的标的

```python
class MomentumStrategy:
    def __init__(self, top_n=3, min_change_pct=3.0):
        self.top_n = 3           # 买入前 3 只
        self.min_change_pct = 3.0 # 涨幅 >= 3%
    
    def generate_signals(self, quotes):
        # 1. 过滤涨幅 >= 3% 的标的
        strong_stocks = [q for q in quotes if q["change_pct"] >= 3.0]
        
        # 2. 按涨幅排序
        strong_stocks.sort(key=lambda x: x["change_pct"], reverse=True)
        
        # 3. 取前 3 只
        return strong_stocks[:self.top_n]
```

**参数**:
- `top_n`: 买入标的数量 (默认 3)
- `min_change_pct`: 最小涨幅阈值 (默认 3%)

### 5.2 均值回归策略 (Mean Reversion Strategy)

**逻辑**: 逢低买入，抄底跌幅较大的标的

```python
class MeanReversionStrategy:
    def __init__(self, top_n=3, max_drop_pct=-3.0):
        self.top_n = 3
        self.max_drop_pct = -3.0  # 跌幅 <= -3%
```

### 5.3 风控管理 (Risk Manager)

**功能**:
- 止损: -10% 清仓
- 止盈: +100% 目标
- 移动止损: 从高点回撤 8%
- 仓位控制: 单只标的最大 30% 资金

```python
class RiskManager:
    def __init__(self, starting_capital=1000000, target_return=1.0, stop_loss=-0.1):
        self.starting_capital = 1000000  # 初始资金 $1M
        self.target_return = 1.0          # 目标收益 +100%
        self.stop_loss = -0.1             # 止损线 -10%
        self.high_water_mark = 0          # 最高点
```

---

## 六、API 接口说明

### 6.1 Rockflow API

**Base URL**: `https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1`

**认证**: `X-API-Key` 请求头

**接口列表**:

| 接口 | 方法 | 说明 |
|------|------|------|
| `/assets` | GET | 获取账户资产 |
| `/positions` | GET | 获取持仓 |
| `/orders` | POST | 下单 |
| `/orders/{id}` | DELETE | 撤单 |
| `/market/tick/latest` | GET | 获取实时行情 |

### 6.2 可交易标的

**美股 (12只)**:
```
NVDA, TSLA, ARM, ASML, PLTR, MU, TSM, CRWV, IREN, NBIS, BABA, BIDU
```

**港股 (7只)**:
```
00700.HK (腾讯), 09988.HK (阿里巴巴-SW), 09888.HK (百度-SW),
00981.HK (中芯国际), 02513.HK (美团), 06869.HK (长飞光纤),
00100.HK (九龙仓置业)
```

---

## 七、定时任务

### 7.1 crontab 配置

```bash
# 美股盘中扫描 - 每20分钟 (北京时间 21:20-04:00)
20,40 21 * * 1-5 cd /path/to/xiaoqiang && python main.py --mode scan >> logs/scan.log 2>&1
0,20,40 22,23 * * 1-5 cd /path/to/xiaoqiang && python main.py --mode scan >> logs/scan.log 2>&1
0,20,40 0,1,2,3 * * 2-6 cd /path/to/xiaoqiang && python main.py --mode scan >> logs/scan.log 2>&1
0,20 4 * * 2-6 cd /path/to/xiaoqiang && python main.py --mode scan >> logs/scan.log 2>&1

# 每日收盘汇报 (北京时间 06:00)
0 6 * * 2-6 cd /path/to/xiaoqiang && python daily_workflow.py --mode report >> logs/report.log 2>&1
```

### 7.2 运行模式

| 模式 | 命令 | 说明 |
|------|------|------|
| 扫描 | `python main.py --mode scan` | 只分析，不下单 |
| 交易 | `python main.py --mode trade` | 分析并下单 |
| 监控 | `python main.py --mode monitor` | 持续监控 |

---

## 八、与财神V8 的协作

### 8.1 分工明确

| 系统 | 市场 | 时间段 | 任务 |
|------|------|--------|------|
| 财神V8 | A股 | 08:00-14:30 | 盘前扫描、盘中监控、复盘 |
| 小强 | 美股 | 21:20-04:00 | 盘中扫描、自动交易 |

### 8.2 数据隔离

- 财神V8: `/home/wade/.openclaw/agents/cfo/workspace/stock-tracker-v8/`
- 小强: `/home/wade/.openclaw/agents/ceo/workspace/xiaoqiang/`

### 8.3 未来整合方向

```python
# 可能的整合方式
class UnifiedQuantSystem:
    def __init__(self):
        self.a_share_engine = CaishenV8()  # A股引擎
        self.us_share_engine = XiaoQiang()  # 美股引擎
    
    def get_global_signals(self):
        """全球市场信号整合"""
        a_signals = self.a_share_engine.scan()
        us_signals = self.us_share_engine.scan()
        
        return {
            "a_share": a_signals,
            "us_share": us_signals,
            "correlation": self.calculate_correlation(a_signals, us_signals)
        }
```

---

## 九、扩展计划

### 9.1 Phase 7: qlib 深度集成

- [ ] 使用 qlib `D.features()` 获取历史数据
- [ ] 接入 qlib 回测引擎
- [ ] 使用 qlib 内置因子

### 9.2 Phase 8: 多策略组合

- [ ] 策略权重动态调整
- [ ] 风险平价配置
- [ ] 最大回撤控制

### 9.3 Phase 9: 机器学习

- [ ] 使用 qlib `MLPredictor`
- [ ] 训练自定义模型
- [ ] 在线学习更新

---

## 十、常见问题

### Q1: 小强和财神V8 有什么区别？

**A**: 小强专注美股+港股，财神V8 专注A股。两者数据源、交易接口完全独立。

### Q2: qlib 在哪里被使用？

**A**: 当前小强系统兼容 qlib 数据格式，但尚未深度使用 qlib 的回测和因子功能。qlib 环境已安装在 `xiaoqiang/venv`。

### Q3: 如何添加新的交易标的？

**A**: 修改 `data/rockflow_config.py`:

```python
US_TICKERS = ["NVDA", "TSLA", "NEW_TICKER"]
HK_TICKERS = ["00700.HK", "NEW_TICKER.HK"]
```

### Q4: 如何调整策略参数？

**A**: 修改 `config.yaml` 或直接在代码中调整:

```python
# main.py
self.momentum_strategy = MomentumStrategy(top_n=5, min_change_pct=2.0)
```

---

## 十一、参考资源

- qlib 官方文档: https://qlib.readthedocs.io/
- Rockflow API 文档: (内部)
- 财神V8 系统: `/home/wade/.openclaw/agents/cfo/workspace/stock-tracker-v8/`

---

*文档维护: CEO Agent (Commander Wade)*  
*最后更新: 2026-04-02*
