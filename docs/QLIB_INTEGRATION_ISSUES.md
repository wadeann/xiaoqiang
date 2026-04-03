# qlib 回测引擎集成限制分析

## 问题现状

当前小强系统**仅兼容 qlib 数据格式**，但未深度使用 qlib 回测引擎。

## 核心限制

### 1. 数据源不匹配

| qlib 要求 | Rockflow API 提供 | 差距 |
|-----------|-------------------|------|
| 本地历史数据存储 | ❌ 只有实时数据 | 需要自己缓存 |
| 日线/分钟级 K线 | ✅ 实时 tick | 缺历史 K线 |
| 交易日历 | ❌ 无 | 需要导入 |
| 美股/港股数据 | ❌ 默认只有 A股 | 需要自己构建 |

### 2. qlib 回测流程

```
qlib 回测流程 (标准):
┌─────────────────┐
│ 1. qlib.init()  │ ← 需要本地数据路径
│   provider_uri  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. D.features() │ ← 查询历史特征
│   获取历史数据   │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. Strategy     │ ← 定义策略类
│   generate()    │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. backtest()   │ ← 运行回测
│   计算收益/风险  │
└─────────────────┘
```

**当前小强缺少**: 步骤 1 和 2

### 3. Rockflow API 限制

```python
# Rockflow 只提供:
- /market/tick/latest  → 实时行情 (当前价格)
- /assets              → 账户资产
- /positions           → 当前持仓
- /orders              → 下单/撤单

# Rockflow 不提供:
- 历史K线数据 (1分钟/5分钟/日线)
- 历史成交明细
- 历史订单记录
- 交易日历
```

### 4. 数据格式差异

**qlib 要求的数据格式**:
```
~/.qlib/qlib_data/us_data/
├── instruments/
│   └── all.txt          # 股票列表
├── features/
│   └── day/
│       └── NVDA/
│           ├── close.bin
│           ├── open.bin
│           ├── high.bin
│           ├── low.bin
│           └── volume.bin
└── calendars/
    └── day.txt          # 交易日历
```

**Rockflow 返回的数据**:
```json
{
  "symbol": "NVDA",
  "tradePrice": 174.0,
  "changePercent": 2.35
}
// 只有当前时刻的数据，无历史
```

## 解决方案

### 方案 A: 构建本地数据仓库 (推荐)

```python
# 1. 每日缓存数据
class DataWarehouse:
    """本地数据仓库"""
    
    def __init__(self):
        self.data_dir = Path("~/.qlib/qlib_data/us_data")
    
    def save_daily_quote(self, symbol, quote):
        """每日收盘后保存日线数据"""
        date = datetime.now().strftime("%Y-%m-%d")
        # 保存到 qlib 格式
        self._save_to_qlib_format(symbol, date, quote)
    
    def save_intraday_quotes(self, symbol, quotes):
        """盘中保存分钟级数据"""
        # 保存到本地缓存
        pass

# 2. 使用 akshare 补充历史数据
import akshare as ak

def get_us_history(symbol, days=365):
    """获取美股历史数据"""
    df = ak.stock_us_daily(symbol=symbol, adjust="qfq")
    return df.tail(days)
```

**优点**:
- 完整使用 qlib 回测能力
- 可运行历史回测
- 可使用 qlib 内置因子

**缺点**:
- 需要时间积累数据
- 需要额外存储空间
- 需要维护数据质量

### 方案 B: 轻量级回测 (当前可行)

```python
# 不依赖 qlib，自己实现简单回测
class SimpleBacktest:
    """轻量级回测引擎"""
    
    def __init__(self, initial_capital=1000000):
        self.capital = initial_capital
        self.trades = []
    
    def run(self, signals, historical_prices):
        """
        signals: 交易信号列表
        historical_prices: 历史价格字典 {symbol: [prices]}
        """
        for date, signal in enumerate(signals):
            if signal['action'] == 'BUY':
                # 模拟买入
                pass
            elif signal['action'] == 'SELL':
                # 模拟卖出
                pass
        
        return self.calculate_metrics()
```

**优点**:
- 立即可用
- 不需要历史数据积累
- 与当前系统无缝集成

**缺点**:
- 功能有限
- 无 qlib 高级特性

### 方案 C: 混合方案 (最佳实践)

```
┌─────────────────────────────────────────────────────────────┐
│                    小强量化系统架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  实时交易层 (当前)                回测分析层 (未来)          │
│  ┌─────────────────┐            ┌─────────────────┐        │
│  │ Rockflow API    │            │ 本地数据仓库    │        │
│  │ - 实时行情      │            │ - 日线数据      │        │
│  │ - 下单交易      │            │ - 分钟数据      │        │
│  └────────┬────────┘            └────────┬────────┘        │
│           │                              │                  │
│           ▼                              ▼                  │
│  ┌─────────────────┐            ┌─────────────────┐        │
│  │ MomentumStrategy│            │ qlib 回测引擎   │        │
│  │ - 实时信号生成  │            │ - 策略回测      │        │
│  │ - 直接下单      │            │ - 因子分析      │        │
│  └─────────────────┘            │ - 风险评估      │        │
│                                 └─────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 实施计划

### Phase 7: 本地数据仓库 (预计 2-3 天)

```bash
# 1. 创建数据目录
mkdir -p ~/.qlib/qlib_data/us_data/{instruments,features/day,calendars}

# 2. 导入美股股票列表
echo "NVDA\nTSLA\nARM\nASML\nPLTR\nMU\nTSM\nCRWV\nIREN\nNBIS\nBABA\nBIDU" > ~/.qlib/qlib_data/us_data/instruments/all.txt

# 3. 每日收盘后保存数据
# 添加到 crontab: 06:00 美股收盘后
0 6 * * 2-6 cd /path/to/xiaoqiang && python data_warehouse.py --save-daily
```

### Phase 8: qlib 回测集成 (预计 1-2 天)

```python
# backtest/qlib_backtest.py
import qlib
from qlib.strategy import TopkDropoutStrategy
from qlib.backtest import backtest

def run_qlib_backtest():
    # 初始化 qlib
    qlib.init(provider_uri='~/.qlib/qlib_data/us_data')
    
    # 运行回测
    portfolio_result = backtest(
        strategy=TopkDropoutStrategy(),
        executor={'time_per_step': 'day'},
        start_time='2025-01-01',
        end_time='2026-04-01',
    )
    
    return portfolio_result
```

## 当前可行的替代方案

由于 Rockflow API 不提供历史数据，当前我们可以：

### 1. 使用 akshare 获取美股历史数据

```python
import akshare as ak

# 获取美股历史 K线
df = ak.stock_us_daily(symbol="NVDA", adjust="qfq")
# 返回: date, open, close, high, low, volume
```

### 2. 自己实现简单回测

已在 `backtest/run_backtest.py` 中实现基础框架。

### 3. 逐步积累数据

每日收盘后自动保存当天的数据，3个月后就有完整的历史数据可用于 qlib 回测。

## 结论

**未使用 qlib 回测的原因**:
1. Rockflow API 只有实时数据，无历史数据
2. qlib 需要本地数据仓库，我们还没有建立
3. qlib 默认只支持 A股，需要自己构建美股/港股数据

**建议**:
- 短期: 使用简单回测 (已实现)
- 中期: 每日积累数据，3个月后启用 qlib 回测
- 长期: 完整集成 qlib 生态

---

*文档更新: 2026-04-02*
