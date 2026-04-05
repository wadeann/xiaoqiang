"""
回测引擎模块 - 策略历史数据回测

包含:
- BacktestEngine: 回测引擎核心类
- BacktestResult: 回测结果数据类
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import (
    OHLCVBar,
    OrderSide,
    Portfolio,
    Signal,
    SignalType,
    Trade,
)
from risk.manager import RiskConfig, RiskManager
from strategies.momentum import BaseStrategy


@dataclass
class BacktestResult:
    """
    回测结果
    汇总回测过程中的所有绩效指标
    """
    strategy_name: str                     # 策略名称
    initial_capital: float                 # 初始资金
    final_value: float                     # 最终权益
    total_return_pct: float                # 总收益率
    max_drawdown_pct: float                # 最大回撤
    sharpe_ratio: float                    # 夏普比率
    total_trades: int                      # 总交易次数
    winning_trades: int                    # 盈利交易次数
    losing_trades: int                     # 亏损交易次数
    win_rate: float                        # 胜率
    avg_win: float                         # 平均盈利
    avg_loss: float                        # 平均亏损
    profit_factor: float                   # 盈亏比
    avg_holding_period: float              # 平均持仓周期
    trades: List[Trade] = field(default_factory=list)  # 交易明细
    equity_curve: List[Dict] = field(default_factory=list)  # 权益曲线

    def summary(self) -> str:
        """生成回测结果摘要文本"""
        lines = [
            "=" * 60,
            f"回测结果: {self.strategy_name}",
            "=" * 60,
            f"初始资金:        {self.initial_capital:>12,.2f}",
            f"最终权益:        {self.final_value:>12,.2f}",
            f"总收益率:        {self.total_return_pct:>11.2f}%",
            f"最大回撤:        {self.max_drawdown_pct:>11.2f}%",
            f"夏普比率:        {self.sharpe_ratio:>12.2f}",
            "-" * 60,
            f"总交易次数:      {self.total_trades:>12}",
            f"盈利交易:        {self.winning_trades:>12}",
            f"亏损交易:        {self.losing_trades:>12}",
            f"胜率:            {self.win_rate:>11.2f}%",
            f"平均盈利:        {self.avg_win:>12,.2f}",
            f"平均亏损:        {self.avg_loss:>12,.2f}",
            f"盈亏比:          {self.profit_factor:>12.2f}",
            f"平均持仓周期:    {self.avg_holding_period:>8.1f} 天",
            "=" * 60,
        ]
        return "\n".join(lines)


class BacktestEngine:
    """
    回测引擎
    
    工作流程:
    1. 初始化策略、风控和组合
    2. 逐根K线遍历历史数据
    3. 策略生成信号 -> 风控审核 -> 执行交易
    4. 监控止损止盈
    5. 记录权益曲线和交易明细
    6. 计算绩效指标
    
    使用示例:
        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(strategy, bars)
        print(result.summary())
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        risk_config: Optional[RiskConfig] = None,
    ):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
            risk_config: 风控配置（可选）
        """
        self.initial_capital = initial_capital
        self.risk_config = risk_config or RiskConfig()
        self._trade_id_counter = 0  # 交易ID计数器

    def run(
        self,
        strategy: BaseStrategy,
        bars: List[OHLCVBar],
    ) -> BacktestResult:
        """
        执行回测
        
        Args:
            strategy: 交易策略实例
            bars: 历史K线数据列表
            
        Returns:
            BacktestResult: 回测结果
        """
        # 初始化投资组合和风控
        portfolio = Portfolio(
            initial_capital=self.initial_capital,
            cash=self.initial_capital,
        )
        risk_manager = RiskManager(self.risk_config)

        # 逐根K线回测
        for i, bar in enumerate(bars):
            # 1. 更新策略数据
            strategy.update(bar)

            # 2. 更新权益曲线
            self._update_portfolio_value(portfolio, bar)
            portfolio.update_equity(bar.timestamp)

            # 3. 更新风控峰值权益
            risk_manager.update_peak_equity(portfolio)

            # 4. 检查持仓的止损止盈
            exit_reason = risk_manager.check_stop_loss_take_profit(portfolio, bar)
            if exit_reason and not portfolio.position_quantity == 0:
                self._close_position(portfolio, bar, exit_reason)
                risk_manager.increment_trade_count()
                continue

            # 5. 策略生成信号
            signal = strategy.generate_signal(bar)

            # 6. 风控验证信号
            if signal.is_actionable and risk_manager.validate_signal(signal, portfolio):
                # 7. 执行交易
                if signal.signal_type == SignalType.BUY:
                    self._open_position(portfolio, signal, bar)
                elif signal.signal_type == SignalType.SELL:
                    self._close_position(portfolio, bar, "signal")

                if signal.is_actionable:
                    risk_manager.increment_trade_count()

        # 回测结束，强制平仓
        if portfolio.position_quantity > 0:
            self._close_position(portfolio, bars[-1], "end_of_backtest")

        # 计算并返回结果
        return self._calculate_result(strategy.name, portfolio)

    def _update_portfolio_value(self, portfolio: Portfolio, bar: OHLCVBar):
        """
        更新投资组合市值
        
        根据当前价格计算持仓市值和账户总值
        
        Args:
            portfolio: 投资组合
            bar: 当前K线
        """
        portfolio.position_value = portfolio.position_quantity * bar.close
        portfolio.total_value = portfolio.cash + portfolio.position_value

    def _open_position(
        self,
        portfolio: Portfolio,
        signal: Signal,
        bar: OHLCVBar,
    ):
        """
        开仓（买入）
        
        计算开仓数量，扣除手续费和滑点成本
        
        Args:
            portfolio: 投资组合
            signal: 买入信号
            bar: 当前K线
        """
        # 如果已有持仓，先不重复开仓
        if portfolio.position_quantity > 0:
            return

        risk_manager = RiskManager(self.risk_config)
        quantity = risk_manager.calculate_position(signal, portfolio)

        if quantity <= 0:
            return

        # 计算成本（含手续费和滑点）
        execution_price = signal.price * (1 + self.risk_config.slippage_rate)
        cost = quantity * execution_price
        commission = cost * self.risk_config.commission_rate
        total_cost = cost + commission

        # 确保现金足够
        if total_cost > portfolio.cash:
            quantity = portfolio.cash / (
                execution_price * (1 + self.risk_config.commission_rate)
            )
            cost = quantity * execution_price
            commission = cost * self.risk_config.commission_rate
            total_cost = cost + commission

        # 执行开仓
        portfolio.cash -= total_cost
        portfolio.position_quantity = quantity
        portfolio.position_avg_price = execution_price
        portfolio.position_value = quantity * execution_price

        # 记录交易
        self._trade_id_counter += 1
        trade = Trade(
            trade_id=self._trade_id_counter,
            side=OrderSide.LONG,
            entry_price=execution_price,
            quantity=quantity,
            entry_time=bar.timestamp,
            commission=commission,
            slippage=cost * self.risk_config.slippage_rate,
        )
        portfolio.trades.append(trade)

    def _close_position(
        self,
        portfolio: Portfolio,
        bar: OHLCVBar,
        reason: str,
    ):
        """
        平仓（卖出）
        
        计算盈亏，更新现金，记录交易
        
        Args:
            portfolio: 投资组合
            bar: 当前K线
            reason: 平仓原因
        """
        if portfolio.position_quantity <= 0:
            return

        # 计算卖出价格（含滑点）
        execution_price = bar.close * (1 - self.risk_config.slippage_rate)
        revenue = portfolio.position_quantity * execution_price
        commission = revenue * self.risk_config.commission_rate
        net_revenue = revenue - commission

        # 计算盈亏
        entry_value = portfolio.position_quantity * portfolio.position_avg_price
        pnl = net_revenue - entry_value
        pnl_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0

        # 更新组合
        portfolio.cash += net_revenue
        portfolio.position_quantity = 0
        portfolio.position_avg_price = 0
        portfolio.position_value = 0

        # 更新最后一笔交易记录
        for trade in reversed(portfolio.trades):
            if trade.is_open:
                trade.exit_price = execution_price
                trade.exit_time = bar.timestamp
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct
                trade.commission += commission
                trade.slippage += revenue * self.risk_config.slippage_rate
                trade.exit_reason = reason
                break

    def _calculate_result(
        self,
        strategy_name: str,
        portfolio: Portfolio,
    ) -> BacktestResult:
        """
        计算回测绩效指标
        
        计算指标:
        - 总收益率
        - 最大回撤
        - 夏普比率
        - 胜率
        - 盈亏比
        - 平均持仓周期
        
        Args:
            strategy_name: 策略名称
            portfolio: 最终投资组合
            
        Returns:
            BacktestResult: 回测结果
        """
        # 获取已平仓交易
        closed_trades = [t for t in portfolio.trades if not t.is_open]
        wins = [t for t in closed_trades if t.pnl > 0]
        losses = [t for t in closed_trades if t.pnl <= 0]

        # 计算最大回撤
        max_drawdown = 0.0
        peak = self.initial_capital
        for point in portfolio.equity_curve:
            if point["total_value"] > peak:
                peak = point["total_value"]
            drawdown = (peak - point["total_value"]) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        # 计算夏普比率（简化版，假设无风险利率为0）
        sharpe_ratio = self._calc_sharpe_ratio(portfolio.equity_curve)

        # 计算平均持仓周期
        holding_periods = [
            t.holding_periods for t in closed_trades if t.holding_periods is not None
        ]
        avg_holding = sum(holding_periods) / len(holding_periods) if holding_periods else 0

        # 计算盈亏比
        total_wins = sum(t.pnl for t in wins)
        total_losses = abs(sum(t.pnl for t in losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

        return BacktestResult(
            strategy_name=strategy_name,
            initial_capital=self.initial_capital,
            final_value=portfolio.total_value,
            total_return_pct=portfolio.return_pct,
            max_drawdown_pct=max_drawdown * 100,
            sharpe_ratio=sharpe_ratio,
            total_trades=len(portfolio.trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=len(wins) / len(closed_trades) * 100 if closed_trades else 0,
            avg_win=total_wins / len(wins) if wins else 0,
            avg_loss=total_losses / len(losses) if losses else 0,
            profit_factor=profit_factor,
            avg_holding_period=avg_holding,
            trades=portfolio.trades,
            equity_curve=portfolio.equity_curve,
        )

    @staticmethod
    def _calc_sharpe_ratio(equity_curve: List[Dict], risk_free_rate: float = 0.0) -> float:
        """
        计算年化夏普比率
        
        夏普比率 = (年化收益率 - 无风险利率) / 年化波动率
        
        Args:
            equity_curve: 权益曲线数据
            risk_free_rate: 无风险利率（默认0）
            
        Returns:
            float: 夏普比率
        """
        if len(equity_curve) < 2:
            return 0.0

        # 计算日收益率序列
        returns = []
        for i in range(1, len(equity_curve)):
            prev_value = equity_curve[i - 1]["total_value"]
            curr_value = equity_curve[i]["total_value"]
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)

        if not returns:
            return 0.0

        # 计算均值和标准差
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_return = variance ** 0.5

        # 年化（假设252个交易日）
        if std_return == 0:
            return 0.0

        annualized_return = mean_return * 252
        annualized_std = std_return * (252 ** 0.5)

        return (annualized_return - risk_free_rate) / annualized_std
