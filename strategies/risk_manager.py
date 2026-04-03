#!/usr/bin/env python3
"""
小强量化系统 - 风控模块
"""

from typing import Dict, List, Optional
from datetime import datetime


class RiskManager:
    """风险管理器"""
    
    def __init__(self, starting_capital: float = 1000000, 
                 target_return: float = 1.0, 
                 stop_loss: float = -0.10,
                 max_position_pct: float = 0.3,
                 max_single_loss_pct: float = 0.05):
        """
        初始化
        
        Args:
            starting_capital: 起始资金
            target_return: 目标收益率 (1.0 = 100%)
            stop_loss: 止损线 (-0.10 = -10%)
            max_position_pct: 单只标的最大仓位比例
            max_single_loss_pct: 单笔交易最大亏损比例
        """
        self.starting_capital = starting_capital
        self.target_return = target_return
        self.stop_loss = stop_loss
        self.max_position_pct = max_position_pct
        self.max_single_loss_pct = max_single_loss_pct
        
        # 状态
        self.total_assets = starting_capital
        self.cash = starting_capital
        self.positions = {}
        self.trade_history = []
    
    def update_assets(self, total: float, cash: float):
        """更新资产"""
        self.total_assets = total
        self.cash = cash
    
    def update_positions(self, positions: List[Dict]):
        """更新持仓"""
        self.positions = {}
        for pos in positions:
            symbol = pos.get("symbol")
            self.positions[symbol] = {
                "quantity": pos.get("quantity", 0),
                "avg_cost": pos.get("avgCost", 0),
                "market_value": pos.get("marketValue", 0)
            }
    
    def get_pnl(self) -> tuple:
        """获取盈亏"""
        pnl = self.total_assets - self.starting_capital
        pnl_rate = pnl / self.starting_capital
        return pnl, pnl_rate
    
    def check_stop_loss(self) -> bool:
        """检查是否触发止损"""
        _, pnl_rate = self.get_pnl()
        return pnl_rate <= self.stop_loss
    
    def check_target(self) -> bool:
        """检查是否达成目标"""
        _, pnl_rate = self.get_pnl()
        return pnl_rate >= self.target_return
    
    def calculate_position_size(self, price: float, capital: Optional[float] = None) -> int:
        """
        计算仓位大小
        
        Args:
            price: 当前价格
            capital: 可用资金
        
        Returns:
            股票数量
        """
        available = capital or self.cash
        max_position_value = self.total_assets * self.max_position_pct
        position_value = min(available, max_position_value)
        
        return int(position_value / price)
    
    def should_reduce_position(self, symbol: str, current_price: float) -> bool:
        """
        是否应该减仓
        
        Args:
            symbol: 标的代码
            current_price: 当前价格
        
        Returns:
            是否减仓
        """
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        avg_cost = pos.get("avg_cost", current_price)
        
        # 计算盈亏比例
        pnl_rate = (current_price - avg_cost) / avg_cost
        
        # 亏损超过阈值，减仓
        if pnl_rate <= -self.max_single_loss_pct:
            return True
        
        return False
    
    def get_risk_report(self) -> Dict:
        """获取风险报告"""
        pnl, pnl_rate = self.get_pnl()
        
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_assets": self.total_assets,
            "cash": self.cash,
            "positions_count": len(self.positions),
            "pnl": pnl,
            "pnl_rate": pnl_rate,
            "pnl_pct": f"{pnl_rate*100:.2f}%",
            "target_return": self.target_return,
            "stop_loss": self.stop_loss,
            "target_reached": self.check_target(),
            "stop_triggered": self.check_stop_loss(),
            "status": "TARGET_REACHED" if self.check_target() else ("STOP_LOSS" if self.check_stop_loss() else "NORMAL")
        }
    
    def record_trade(self, trade: Dict):
        """记录交易"""
        trade["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.trade_history.append(trade)
    
    def get_trade_summary(self) -> Dict:
        """获取交易统计"""
        if not self.trade_history:
            return {"total_trades": 0}
        
        buy_trades = [t for t in self.trade_history if t.get("side") == "BUY"]
        sell_trades = [t for t in self.trade_history if t.get("side") == "SELL"]
        
        return {
            "total_trades": len(self.trade_history),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_volume": sum(t.get("value", 0) for t in self.trade_history)
        }


# 测试代码
if __name__ == "__main__":
    # 初始化风控
    risk = RiskManager(
        starting_capital=1000000,
        target_return=1.0,
        stop_loss=-0.10,
        max_position_pct=0.3
    )
    
    # 模拟更新资产
    risk.update_assets(1050000, 500000)
    
    # 计算仓位
    price = 150.0
    qty = risk.calculate_position_size(price)
    print(f"价格 ${price:.2f}，建议买入 {qty} 股 (约 ${qty * price:,.0f})")
    
    # 风险报告
    report = risk.get_risk_report()
    print("\n风险报告:")
    for key, value in report.items():
        print(f"  {key}: {value}")
