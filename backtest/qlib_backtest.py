#!/usr/bin/env python3
"""
小强量化系统 - qlib 增强回测
支持: 多因子分析、风险评估、可视化报告
"""

import os
import sys
import json
import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 禁用代理
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.a_share_data import AShareDataFetcher


class MultiFactorAnalyzer:
    """多因子分析器"""
    
    def __init__(self):
        self.factors = ['momentum', 'volume', 'turnover', 'volatility', 'ma_distance']
    
    def calculate_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算多因子"""
        df = df.copy()
        
        # 确保数值列
        for col in ['open', 'close', 'high', 'low', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 1. 动量因子 (5日、10日、20日收益率)
        df['return_5d'] = df['close'].pct_change(5) * 100
        df['return_10d'] = df['close'].pct_change(10) * 100
        df['return_20d'] = df['close'].pct_change(20) * 100
        
        # 2. 成交量因子 (成交量比率)
        df['volume_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma5'] * 100
        
        # 3. 换手率因子 (如果有)
        if 'turnover' in df.columns:
            df['turnover_ma5'] = df['turnover'].rolling(5).mean()
            df['turnover_ratio'] = df['turnover'] / df['turnover_ma5'] * 100
        
        # 4. 波动率因子 (20日收益率标准差)
        df['volatility'] = df['close'].pct_change().rolling(20).std() * 100
        
        # 5. 均线距离因子
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma_distance_5'] = (df['close'] - df['ma5']) / df['ma5'] * 100
        df['ma_distance_10'] = (df['close'] - df['ma10']) / df['ma10'] * 100
        df['ma_distance_20'] = (df['close'] - df['ma20']) / df['ma20'] * 100
        
        # 6. 综合得分 (加权平均)
        weights = {
            'return_5d': 0.25,
            'return_10d': 0.15,
            'volume_ratio': 0.15,
            'volatility': -0.10,  # 波动率越低越好
            'ma_distance_5': 0.20,
            'ma_distance_10': 0.15,
        }
        
        df['score'] = 0
        for factor, weight in weights.items():
            if factor in df.columns:
                normalized = (df[factor] - df[factor].mean()) / (df[factor].std() + 1e-6)
                df['score'] += normalized * weight
        
        return df


class EnhancedBacktest:
    """增强回测引擎"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.starting_capital = self.config.get("trading", {}).get("starting_capital", 1000000)
        self.target_return = self.config.get("trading", {}).get("target_return", 1.0)
        self.stop_loss = self.config.get("trading", {}).get("stop_loss", -0.10)
        self.analyzer = MultiFactorAnalyzer()
        self.data_fetcher = AShareDataFetcher()
        self.reset()
    
    def _load_config(self, config_path: str) -> dict:
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
        self.factor_records = []
    
    def load_data(self, symbols: List[str], days: int = 60) -> Dict[str, pd.DataFrame]:
        """加载历史数据"""
        print(f"📥 加载 A股历史数据 ({days} 天)...")
        data = {}
        
        # 导入回测引擎的数据加载器
        from backtest.run_backtest import DataLoader
        loader = DataLoader()
        
        for symbol in symbols:
            try:
                df = loader.load_a_share_history(symbol, days=days)
                if df is not None and not df.empty:
                    # 计算多因子
                    df = self.analyzer.calculate_factors(df)
                    df['symbol'] = symbol
                    data[symbol] = df
                    print(f"  ✅ {symbol}: {len(df)} 条记录, 多因子已计算")
            except Exception as e:
                print(f"  ❌ {symbol}: {e}")
        
        return data
    
    def run_backtest(
        self, 
        data: Dict[str, pd.DataFrame],
        strategy: str = "multi_factor",
        position_size: float = 0.2,
        max_positions: int = 5,
        commission: float = 0.001,
        slippage: float = 0.001,
        top_n: int = 3,
        min_score: float = 0.5
    ) -> Dict:
        """运行回测"""
        print("=" * 70)
        print("📊 qlib 增强回测引擎 v1.0")
        print("=" * 70)
        print(f"策略: {strategy}")
        print(f"起始资金: ¥{self.starting_capital:,.0f}")
        print(f"目标收益: {self.target_return*100}%")
        print(f"止损线: {self.stop_loss*100}%")
        print(f"单只仓位: {position_size*100}%")
        print(f"最大持仓: {max_positions}只")
        print(f"选股数量: Top {top_n}")
        print(f"最低得分: {min_score}")
        print("=" * 70)
        
        self.reset()
        
        # 获取所有交易日期
        all_dates = set()
        for symbol, df in data.items():
            if not df.empty and 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                all_dates.update(df['date'].tolist())
        
        all_dates = sorted(list(all_dates))
        
        if not all_dates:
            return {"error": "No data available"}
        
        print(f"\n📅 回测期间: {all_dates[0]} ~ {all_dates[-1]} ({len(all_dates)} 个交易日)")
        print(f"📈 标的数量: {len(data)}")
        
        # 逐日回测
        for i, date in enumerate(all_dates):
            # 获取当日行情和多因子数据
            daily_bars = []
            daily_scores = []
            
            for symbol, df in data.items():
                if 'date' in df.columns and date in df['date'].values:
                    row = df[df['date'] == date].iloc[-1]
                    bar = row.to_dict()
                    bar['symbol'] = symbol
                    daily_bars.append(bar)
                    if 'score' in bar and not pd.isna(bar['score']):
                        daily_scores.append((symbol, bar['score'], bar.get('close', 0)))
            
            if not daily_bars:
                continue
            
            # 计算权益
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
                self._liquidate_all(daily_bars, commission, slippage, date)
                break
            
            # 生成信号
            signals = self._generate_signals(
                daily_bars, daily_scores, strategy, top_n, min_score
            )
            
            # 记录因子
            if daily_scores:
                self.factor_records.append({
                    "date": date,
                    "scores": daily_scores[:5]  # Top 5
                })
            
            # 执行交易
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
                    bar['symbol'] = symbol
                    final_bars.append(bar)
            self._liquidate_all(final_bars, commission, slippage, all_dates[-1])
        
        # 计算结果
        results = self._calculate_results()
        return results
    
    def _generate_signals(
        self, 
        daily_bars: List[Dict], 
        daily_scores: List[Tuple],
        strategy: str,
        top_n: int,
        min_score: float
    ) -> List[Dict]:
        """生成交易信号"""
        signals = []
        
        if strategy == "multi_factor":
            # 多因子策略：选择得分最高的股票
            sorted_scores = sorted(daily_scores, key=lambda x: x[1], reverse=True)
            
            for symbol, score, price in sorted_scores[:top_n]:
                if score >= min_score:
                    # 检查是否已持有
                    if symbol not in self.positions:
                        signals.append({
                            "action": "BUY",
                            "symbol": symbol,
                            "price": price,
                            "score": score,
                            "reason": f"多因子得分: {score:.2f}"
                        })
            
            # 卖出得分下降的持仓
            current_scores = {s: sc for s, sc, _ in daily_scores}
            for symbol in list(self.positions.keys()):
                if symbol in current_scores:
                    score = current_scores[symbol]
                    if score < -min_score:  # 得分转负
                        bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
                        if bar:
                            signals.append({
                                "action": "SELL",
                                "symbol": symbol,
                                "price": bar['close'],
                                "score": score,
                                "reason": f"多因子得分转负: {score:.2f}"
                            })
        
        elif strategy == "momentum":
            # 动量策略：买入涨幅最大的股票
            sorted_bars = sorted(daily_bars, key=lambda x: x.get('change_pct', 0), reverse=True)
            
            for bar in sorted_bars[:top_n]:
                change_pct = bar.get('change_pct', 0)
                if change_pct > 2:  # 涨幅超过 2%
                    if bar['symbol'] not in self.positions:
                        signals.append({
                            "action": "BUY",
                            "symbol": bar['symbol'],
                            "price": bar['close'],
                            "change_pct": change_pct,
                            "reason": f"动量信号: +{change_pct:.2f}%"
                        })
        
        return signals
    
    def _calculate_equity(self, daily_bars: List[Dict]) -> float:
        """计算权益"""
        equity = self.cash
        for symbol, position in self.positions.items():
            bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
            if bar:
                equity += position["quantity"] * bar["close"]
            else:
                equity += position["quantity"] * position["avg_price"]
        return equity
    
    def _execute_buy(self, signal: Dict, commission: float, slippage: float, position_size: float):
        """执行买入"""
        symbol = signal["symbol"]
        price = signal["price"]
        
        position_value = self.cash * position_size
        slippage_price = price * (1 + slippage)
        quantity = int(position_value / slippage_price / 100) * 100  # A股一手100股
        
        if quantity < 100:
            return
        
        trade_value = quantity * slippage_price
        commission_fee = max(trade_value * commission, 5.0)  # 最低5元
        total_cost = trade_value + commission_fee
        
        if total_cost > self.cash:
            return
        
        self.cash -= total_cost
        
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
        
        self.trades.append({
            "type": "BUY",
            "symbol": symbol,
            "price": slippage_price,
            "quantity": quantity,
            "value": trade_value,
            "commission": commission_fee,
            "date": signal.get("date", ""),
            "reason": signal.get("reason", "")
        })
    
    def _execute_sell(self, signal: Dict, commission: float, slippage: float):
        """执行卖出"""
        symbol = signal["symbol"]
        price = signal["price"]
        
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        quantity = position["quantity"]
        
        slippage_price = price * (1 - slippage)
        trade_value = quantity * slippage_price
        commission_fee = max(trade_value * commission, 5.0)
        
        self.cash += trade_value - commission_fee
        
        pnl = trade_value - position["total_cost"]
        pnl_rate = pnl / position["total_cost"]
        
        self.trades.append({
            "type": "SELL",
            "symbol": symbol,
            "price": slippage_price,
            "quantity": quantity,
            "value": trade_value,
            "commission": commission_fee,
            "pnl": pnl,
            "pnl_rate": pnl_rate,
            "date": signal.get("date", ""),
            "reason": signal.get("reason", "")
        })
        
        del self.positions[symbol]
    
    def _liquidate_all(self, daily_bars: List[Dict], commission: float, slippage: float, date: str):
        """清仓"""
        for symbol in list(self.positions.keys()):
            bar = next((b for b in daily_bars if b['symbol'] == symbol), None)
            if bar:
                self._execute_sell({
                    "symbol": symbol,
                    "price": bar['close'],
                    "date": date,
                    "reason": "清仓"
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
            "trades": self.trades,
            "factor_records": self.factor_records
        }
    
    def print_results(self, results: Dict):
        """打印回测结果"""
        print("\n" + "=" * 70)
        print("📊 回测结果")
        print("=" * 70)
        print(f"起始资金: ¥{results['starting_capital']:,.0f}")
        print(f"最终权益: ¥{results['final_equity']:,.0f}")
        print(f"总盈亏: ¥{results['pnl']:,.0f} ({results['pnl_pct']})")
        print(f"最大回撤: {results['max_drawdown_pct']}")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"总交易次数: {results['total_trades']}")
        print(f"买入次数: {results['buy_trades']}")
        print(f"卖出次数: {results['sell_trades']}")
        print(f"胜率: {results['win_rate_pct']}")
        print(f"平均盈利: ¥{results['avg_win']:,.0f}")
        print(f"平均亏损: ¥{results['avg_loss']:,.0f}")
        print(f"盈亏比: {results['profit_factor']:.2f}")
        print(f"达成目标: {'✅ 是' if results['target_reached'] else '❌ 否'}")
        print(f"触发止损: {'⚠️ 是' if results['stop_triggered'] else '✅ 否'}")
        print("=" * 70)
    
    def generate_report(self, results: Dict, output_dir: str = "reports"):
        """生成可视化报告"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. 保存权益曲线
        if results.get("equity_curve"):
            equity_df = pd.DataFrame(results["equity_curve"])
            equity_file = output_path / f"equity_curve_{timestamp}.csv"
            equity_df.to_csv(equity_file, index=False)
            print(f"📈 权益曲线已保存: {equity_file}")
        
        # 2. 保存交易记录
        if results.get("trades"):
            trades_df = pd.DataFrame(results["trades"])
            trades_file = output_path / f"trades_{timestamp}.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"📋 交易记录已保存: {trades_file}")
        
        # 3. 保存因子记录
        if results.get("factor_records"):
            factor_rows = []
            for record in results["factor_records"]:
                for symbol, score, price in record["scores"]:
                    factor_rows.append({
                        "date": record["date"],
                        "symbol": symbol,
                        "score": score,
                        "price": price
                    })
            factor_df = pd.DataFrame(factor_rows)
            factor_file = output_path / f"factors_{timestamp}.csv"
            factor_df.to_csv(factor_file, index=False)
            print(f"📊 因子记录已保存: {factor_file}")
        
        # 4. 生成摘要报告
        summary = {
            "timestamp": timestamp,
            "strategy": "multi_factor",
            "starting_capital": results["starting_capital"],
            "final_equity": results["final_equity"],
            "pnl": results["pnl"],
            "pnl_rate": results["pnl_rate"],
            "max_drawdown": results["max_drawdown"],
            "sharpe_ratio": results["sharpe_ratio"],
            "win_rate": results["win_rate"],
            "total_trades": results["total_trades"],
            "profit_factor": results["profit_factor"]
        }
        
        summary_file = output_path / f"summary_{timestamp}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"📄 摘要报告已保存: {summary_file}")
        
        return summary


if __name__ == "__main__":
    # 获取A股标的列表
    from data.rockflow_config import A_SHARE_TICKERS
    
    # 创建回测引擎
    engine = EnhancedBacktest()
    
    # 加载数据
    symbols = A_SHARE_TICKERS[:10]  # 测试前10只
    data = engine.load_data(symbols, days=60)
    
    if data:
        # 运行多因子策略回测
        results = engine.run_backtest(
            data, 
            strategy="multi_factor",
            position_size=0.2,
            max_positions=5,
            top_n=3,
            min_score=0.3
        )
        
        # 打印结果
        engine.print_results(results)
        
        # 生成报告
        engine.generate_report(results)
    else:
        print("❌ 没有加载数据")
