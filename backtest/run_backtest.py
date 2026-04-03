#!/usr/bin/env python3
"""
小强量化系统 - 回测引擎 v2.0
支持: 历史数据下载、多策略回测、参数优化、可视化报告
"""

import json
import yaml
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time


class DataLoader:
    """历史数据加载器"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_a_share_history(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """加载 A股历史数据 (使用东方财富)"""
        cache_file = self.cache_dir / f"{symbol}_{days}d.csv"
        
        # 检查缓存
        if cache_file.exists():
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - cache_time < timedelta(hours=1):
                return pd.read_csv(cache_file)
        
        # 转换代码格式 (300308.SZ -> 0300308)
        code = symbol.replace(".SZ", "").replace(".SH", "")
        if symbol.endswith(".SZ"):
            secid = f"0.{code}"
        else:
            secid = f"1.{code}"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
            "klt": "101",  # 日K
            "fqt": "1",    # 前复权
            "beg": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get("data") and data["data"].get("klines"):
                klines = data["data"]["klines"]
                # 东方财富返回 11 个字段
                columns = ["date", "open", "close", "high", "low", "volume", "amount",
                          "amplitude", "change_pct", "change", "turnover"]
                
                parsed_data = []
                for k in klines:
                    parts = k.split(",")
                    if len(parts) >= 11:
                        parsed_data.append(parts[:11])
                
                df = pd.DataFrame(parsed_data, columns=columns)
                
                # 转换类型
                for col in ["open", "close", "high", "low", "volume", "amount", "change_pct"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                
                df["symbol"] = symbol
                df.to_csv(cache_file, index=False)
                return df
        except Exception as e:
            print(f"  加载 {symbol} 历史数据失败: {e}")
        
        return pd.DataFrame()
    
    def load_us_share_history(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """加载美股历史数据 (使用 yfinance 或其他源)"""
        cache_file = self.cache_dir / f"{symbol}_{days}d.csv"
        
        # 检查缓存
        if cache_file.exists():
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - cache_time < timedelta(hours=6):
                return pd.read_csv(cache_file)
        
        # 尝试使用 yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            df = ticker.history(start=start_date, end=end_date)
            
            if not df.empty:
                df = df.reset_index()
                df["symbol"] = symbol
                df["change_pct"] = ((df["Close"] - df["Close"].shift(1)) / df["Close"].shift(1) * 100).fillna(0)
                df = df.rename(columns={
                    "Date": "date",
                    "Open": "open",
                    "Close": "close",
                    "High": "high",
                    "Low": "low",
                    "Volume": "volume"
                })
                df.to_csv(cache_file, index=False)
                return df[["date", "open", "close", "high", "low", "volume", "change_pct", "symbol"]]
        except Exception as e:
            print(f"  yfinance 加载失败: {e}")
        
        return pd.DataFrame()


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.starting_capital = self.config.get("trading", {}).get("starting_capital", 1000000)
        self.target_return = self.config.get("trading", {}).get("target_return", 1.0)
        self.stop_loss = self.config.get("trading", {}).get("stop_loss", -0.10)
        
        # 回测状态
        self.reset()
        
        # 数据加载器
        self.data_loader = DataLoader()
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置"""
        config_file = Path(__file__).parent.parent / config_path
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}
    
    def reset(self):
        """重置回测状态"""
        self.cash = self.starting_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
    
    def run_backtest(self, data: Dict[str, pd.DataFrame], strategy, 
                      commission: float = 0.001, 
                      slippage: float = 0.001,
                      position_size: float = 0.2,
                      max_positions: int = 5) -> Dict:
        """
        运行回测
        
        Args:
            data: {symbol: DataFrame} 格式的历史数据
            strategy: 策略对象
            commission: 佣金费率 (默认 0.1%)
            slippage: 滑点 (默认 0.1%)
            position_size: 单只股票仓位比例 (默认 20%)
            max_positions: 最大持仓数量 (默认 5)
        
        Returns:
            回测结果
        """
        print("=" * 60)
        print("📊 回测引擎启动 v2.0")
        print("=" * 60)
        print(f"起始资金: ${self.starting_capital:,.0f}")
        print(f"目标收益: {self.target_return*100}%")
        print(f"止损线: {self.stop_loss*100}%")
        print(f"佣金费率: {commission*100}%")
        print(f"滑点: {slippage*100}%")
        print(f"单只仓位: {position_size*100}%")
        print(f"最大持仓: {max_positions}只")
        print("=" * 60)
        
        self.reset()
        
        # 获取所有交易日期
        all_dates = set()
        for symbol, df in data.items():
            if not df.empty:
                all_dates.update(df["date"].tolist())
        
        all_dates = sorted(list(all_dates))
        
        if not all_dates:
            return {"error": "No data available"}
        
        print(f"\n📅 回测期间: {all_dates[0]} ~ {all_dates[-1]} ({len(all_dates)} 个交易日)")
        print(f"📈 标的数量: {len(data)}")
        
        # 逐日回测
        for i, date in enumerate(all_dates):
            # 获取当日行情
            daily_bars = []
            for symbol, df in data.items():
                if date in df["date"].values:
                    bar = df[df["date"] == date].iloc[0].to_dict()
                    bar["symbol"] = symbol
                    daily_bars.append(bar)
            
            if not daily_bars:
                continue
            
            # 计算当日权益
            equity = self._calculate_equity(daily_bars)
            self.equity_curve.append({
                "date": date,
                "equity": equity,
                "cash": self.cash,
                "positions": len(self.positions)
            })
            
            # 检查止损
            pnl_rate = (equity - self.starting_capital) / self.starting_capital
            if pnl_rate <= self.stop_loss:
                print(f"\n⚠️ {date} 触发止损线 ({pnl_rate*100:.2f}%)")
                self._liquidate_all(daily_bars, commission, slippage)
                break
            
            # 生成信号
            try:
                signals = strategy.generate_signals(daily_bars, self.positions)
            except:
                # 旧版策略兼容
                signals = strategy.generate_signals(daily_bars)
            
            # 执行信号
            for signal in signals:
                if signal["action"] == "BUY" and len(self.positions) < max_positions:
                    self._execute_buy(signal, commission, slippage, position_size)
                elif signal["action"] == "SELL":
                    self._execute_sell(signal, commission, slippage)
        
        # 强制平仓
        if self.positions:
            final_bars = []
            for symbol, df in data.items():
                if not df.empty:
                    bar = df.iloc[-1].to_dict()
                    bar["symbol"] = symbol
                    final_bars.append(bar)
            self._liquidate_all(final_bars, commission, slippage)
        
        # 计算结果
        results = self._calculate_results()
        
        return results
    
    def _calculate_equity(self, daily_bars: List[Dict]) -> float:
        """计算权益"""
        equity = self.cash
        
        for symbol, position in self.positions.items():
            bar = next((b for b in daily_bars if b["symbol"] == symbol), None)
            if bar:
                equity += position["quantity"] * bar["close"]
            else:
                equity += position["quantity"] * position["avg_price"]
        
        return equity
    
    def _execute_buy(self, signal: Dict, commission: float, slippage: float, position_size: float):
        """执行买入"""
        symbol = signal["symbol"]
        price = signal["price"]
        
        # 计算仓位
        position_value = self.cash * position_size
        slippage_price = price * (1 + slippage)
        quantity = int(position_value / slippage_price)
        
        if quantity < 1:
            return
        
        # 计算成本
        trade_value = quantity * slippage_price
        commission_fee = max(trade_value * commission, 1.0)
        total_cost = trade_value + commission_fee
        
        if total_cost > self.cash:
            return
        
        # 扣除资金
        self.cash -= total_cost
        
        # 记录持仓
        if symbol in self.positions:
            old = self.positions[symbol]
            new_qty = old["quantity"] + quantity
            new_cost = old["total_cost"] + total_cost
            self.positions[symbol] = {
                "quantity": new_qty,
                "avg_price": new_cost / new_qty,
                "total_cost": new_cost
            }
        else:
            self.positions[symbol] = {
                "quantity": quantity,
                "avg_price": slippage_price,
                "total_cost": total_cost
            }
        
        # 记录交易
        self.trades.append({
            "type": "BUY",
            "symbol": symbol,
            "price": slippage_price,
            "quantity": quantity,
            "value": trade_value,
            "commission": commission_fee,
            "date": signal.get("date", "")
        })
    
    def _execute_sell(self, signal: Dict, commission: float, slippage: float):
        """执行卖出"""
        symbol = signal["symbol"]
        price = signal["price"]
        
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        quantity = position["quantity"]
        
        # 计算收入
        slippage_price = price * (1 - slippage)
        trade_value = quantity * slippage_price
        commission_fee = max(trade_value * commission, 1.0)
        
        # 增加资金
        self.cash += trade_value - commission_fee
        
        # 计算盈亏
        pnl = trade_value - position["total_cost"]
        pnl_rate = pnl / position["total_cost"]
        
        # 记录交易
        self.trades.append({
            "type": "SELL",
            "symbol": symbol,
            "price": slippage_price,
            "quantity": quantity,
            "value": trade_value,
            "commission": commission_fee,
            "pnl": pnl,
            "pnl_rate": pnl_rate,
            "date": signal.get("date", "")
        })
        
        # 删除持仓
        del self.positions[symbol]
    
    def _liquidate_all(self, daily_bars: List[Dict], commission: float, slippage: float):
        """清仓"""
        for symbol in list(self.positions.keys()):
            bar = next((b for b in daily_bars if b["symbol"] == symbol), None)
            if bar:
                self._execute_sell({
                    "symbol": symbol,
                    "price": bar["close"],
                    "date": bar.get("date", "")
                }, commission, slippage)
    
    def _calculate_results(self) -> Dict:
        """计算回测结果"""
        if not self.equity_curve:
            return {"error": "No equity data"}
        
        final_equity = self.equity_curve[-1]["equity"]
        pnl = final_equity - self.starting_capital
        pnl_rate = pnl / self.starting_capital
        
        # 计算最大回撤
        max_equity = self.starting_capital
        max_drawdown = 0
        for record in self.equity_curve:
            if record["equity"] > max_equity:
                max_equity = record["equity"]
            drawdown = (max_equity - record["equity"]) / max_equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 计算夏普比率
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev = self.equity_curve[i-1]["equity"]
                curr = self.equity_curve[i]["equity"]
                returns.append((curr - prev) / prev)
            
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe = (avg_return * 252) / (std_return * np.sqrt(252)) if std_return > 0 else 0
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        # 计算胜率
        sell_trades = [t for t in self.trades if t["type"] == "SELL"]
        winning_trades = [t for t in sell_trades if t.get("pnl", 0) > 0]
        win_rate = len(winning_trades) / len(sell_trades) if sell_trades else 0
        
        # 计算平均盈亏
        avg_win = np.mean([t["pnl"] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t["pnl"] for t in sell_trades if t.get("pnl", 0) < 0]) or 0
        
        return {
            "starting_capital": self.starting_capital,
            "final_equity": final_equity,
            "pnl": pnl,
            "pnl_rate": pnl_rate,
            "pnl_pct": f"{pnl_rate*100:.2f}%",
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": f"{max_drawdown*100:.2f}%",
            "sharpe_ratio": sharpe,
            "total_trades": len(self.trades),
            "buy_trades": len([t for t in self.trades if t["type"] == "BUY"]),
            "sell_trades": len(sell_trades),
            "win_rate": win_rate,
            "win_rate_pct": f"{win_rate*100:.2f}%",
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            "target_reached": pnl_rate >= self.target_return,
            "stop_triggered": pnl_rate <= self.stop_loss,
            "equity_curve": self.equity_curve,
            "trades": self.trades
        }
    
    def print_results(self, results: Dict):
        """打印回测结果"""
        print("\n" + "=" * 60)
        print("📊 回测结果")
        print("=" * 60)
        print(f"起始资金: ${results['starting_capital']:,.0f}")
        print(f"最终权益: ${results['final_equity']:,.0f}")
        print(f"总盈亏: ${results['pnl']:,.0f} ({results['pnl_pct']})")
        print(f"最大回撤: {results['max_drawdown_pct']}")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"总交易次数: {results['total_trades']}")
        print(f"买入次数: {results['buy_trades']}")
        print(f"卖出次数: {results['sell_trades']}")
        print(f"胜率: {results['win_rate_pct']}")
        print(f"平均盈利: ${results['avg_win']:,.0f}")
        print(f"平均亏损: ${results['avg_loss']:,.0f}")
        print(f"盈亏比: {results['profit_factor']:.2f}")
        print(f"达成目标: {'✅ 是' if results['target_reached'] else '❌ 否'}")
        print(f"触发止损: {'⚠️ 是' if results['stop_triggered'] else '✅ 否'}")
        print("=" * 60)
    
    def save_results(self, results: Dict, filename: str = None):
        """保存回测结果"""
        if filename is None:
            filename = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = Path(__file__).parent / "results" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 移除不能序列化的数据
        save_data = {k: v for k, v in results.items() if k not in ["equity_curve", "trades"]}
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 回测结果已保存: {filepath}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from strategies.momentum import MomentumStrategy
    from data.rockflow_config import A_SHARE_TICKERS
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    # 加载历史数据
    print("📥 加载历史数据...")
    data = {}
    for symbol in A_SHARE_TICKERS[:5]:  # 测试前5只
        df = engine.data_loader.load_a_share_history(symbol, days=60)
        if not df.empty:
            data[symbol] = df
            print(f"  {symbol}: {len(df)} 条记录")
    
    if data:
        # 运行回测
        strategy = MomentumStrategy(top_n=2, min_change_pct=3.0)
        results = engine.run_backtest(data, strategy)
        
        # 打印结果
        engine.print_results(results)
        
        # 保存结果
        engine.save_results(results)
    else:
        print("❌ 没有加载到历史数据")
