# 小强量化系统 (XiaoQiang Quant System)

## 简介

小强量化系统是基于 qlib 框架的专业量化交易平台，集成 Rockflow 交易 API。

## 目录结构

```
xiaoqiang/
├── data/           # 数据模块
│   └── cache/      # 数据缓存
├── strategies/     # 策略模块
├── backtest/       # 回测引擎
├── executor/       # 交易执行
├── monitor/        # 监控系统
├── optimizer/      # 优化器
├── utils/          # 工具函数
├── logs/           # 日志目录
├── venv/           # Python 虚拟环境
├── config.yaml     # 配置文件
├── main.py         # 主程序
├── test_qlib.py    # 测试脚本
└── README.md       # 本文件
```

## 安装

```bash
cd /home/wade/.openclaw/agents/ceo/workspace/xiaoqiang
source venv/bin/activate
pip install -r requirements.txt  # 如果有
```

## 使用

```bash
source venv/bin/activate
python main.py
```

## 配置

编辑 `config.yaml` 修改 API 配置和交易参数。

## 开发阶段

- [x] Phase 1: 环境整合 ✅
- [x] Phase 2: 数据层对接 ✅
- [x] Phase 3: 策略开发 ✅
- [x] Phase 4: 回测引擎 ✅
- [x] Phase 5: 实盘对接 ✅
- [x] Phase 6: 监控优化 ✅

### Phase 2 完成内容 (2026-04-01)

**已实现**:
- `data/rockflow_adapter.py` - Rockflow API 数据适配器
- `data/realtime_fetcher.py` - 实时数据获取器
- `data/cache.py` - 数据缓存管理
- `data/rockflow_config.py` - 配置加载
- `strategies/momentum.py` - 动量策略
- `main.py` - 主程序集成

**功能**:
- ✅ 实时扫描 19 只标的行情
- ✅ 自动识别 Top 5 涨幅股
- ✅ 生成买入信号
- ✅ 数据转换为 qlib DataFrame 格式
- ✅ 本地缓存机制

### Phase 3-6 完成内容 (2026-04-01 08:57)

**策略模块**:
- `strategies/momentum.py` - 动量策略 (追涨)
- `strategies/mean_reversion.py` - 均值回归策略 (抄底)
- `strategies/trend_following.py` - 趋势跟踪策略 (MA)
- `strategies/risk_manager.py` - 风控模块

**回测引擎**:
- `backtest/run_backtest.py` - 完整回测框架
- 支持佣金、滑点模拟
- 计算最大回撤、胜率等指标

**交易执行**:
- `executor/trader.py` - 交易执行器
- `executor/signal_filter.py` - 信号过滤器

**监控看板**:
- `monitor/dashboard.py` - 实时监控

**完整系统**:
- `main.py` - 主程序集成
- 支持 3 种运行模式: scan / trade / monitor

## 依赖

- pyqlib 0.9.7
- numpy 2.4.4
- pandas 2.3.3
- akshare 1.18.49
- torch (待安装)

## 创建时间

2026-04-01

## 创建者

CEO Agent (Commander Wade)
