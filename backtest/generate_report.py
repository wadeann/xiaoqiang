#!/usr/bin/env python3
"""
小强量化系统 - 可视化报告生成器
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

def generate_html_report(summary_file: str, trades_file: str, factors_file: str, equity_file: str):
    """生成 HTML 可视化报告"""
    
    # 读取数据
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    trades_df = pd.read_csv(trades_file)
    factors_df = pd.read_csv(factors_file)
    equity_df = pd.read_csv(equity_file)
    
    # 计算交易统计
    buy_trades = trades_df[trades_df['type'] == 'BUY']
    sell_trades = trades_df[trades_df['type'] == 'SELL']
    winning_trades = sell_trades[sell_trades['pnl'] > 0]
    losing_trades = sell_trades[sell_trades['pnl'] < 0]
    
    # 按股票统计
    stock_stats = sell_trades.groupby('symbol').agg({
        'pnl': ['sum', 'mean', 'count'],
        'pnl_rate': 'mean'
    }).round(2)
    stock_stats.columns = ['总盈亏', '平均盈亏', '交易次数', '平均收益率']
    stock_stats = stock_stats.sort_values('总盈亏', ascending=False)
    
    # 生成 HTML
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小强量化系统 - 回测报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #00ff88; margin-bottom: 20px; font-size: 2em; }}
        h2 {{ color: #00ccff; margin: 30px 0 15px; font-size: 1.5em; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .card {{ background: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #333; }}
        .card h3 {{ color: #888; font-size: 0.9em; margin-bottom: 10px; }}
        .card .value {{ font-size: 2em; font-weight: bold; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff4444; }}
        .neutral {{ color: #ffcc00; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ color: #888; font-weight: 500; }}
        tr:hover {{ background: #1a1a1a; }}
        .chart-container {{ background: #1a1a1a; border-radius: 12px; padding: 20px; margin: 20px 0; }}
        .bar {{ display: flex; align-items: center; margin: 10px 0; }}
        .bar-label {{ width: 100px; color: #888; }}
        .bar-fill {{ height: 20px; border-radius: 4px; transition: width 0.5s; }}
        .bar-value {{ margin-left: 10px; font-size: 0.9em; }}
        .timestamp {{ color: #666; font-size: 0.8em; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🐉 小强量化系统 - 回测报告</h1>
        
        <h2>📊 核心指标</h2>
        <div class="grid">
            <div class="card">
                <h3>起始资金</h3>
                <div class="value">¥{summary['starting_capital']:,.0f}</div>
            </div>
            <div class="card">
                <h3>最终权益</h3>
                <div class="value">¥{summary['final_equity']:,.0f}</div>
            </div>
            <div class="card">
                <h3>总盈亏</h3>
                <div class="value {'positive' if summary['pnl'] > 0 else 'negative'}">¥{summary['pnl']:,.0f}</div>
            </div>
            <div class="card">
                <h3>收益率</h3>
                <div class="value {'positive' if summary['pnl_rate'] > 0 else 'negative'}">{summary['pnl_rate']*100:.2f}%</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>最大回撤</h3>
                <div class="value negative">{summary['max_drawdown']*100:.2f}%</div>
            </div>
            <div class="card">
                <h3>夏普比率</h3>
                <div class="value {'positive' if summary['sharpe_ratio'] > 1 else 'neutral'}">{summary['sharpe_ratio']:.2f}</div>
            </div>
            <div class="card">
                <h3>胜率</h3>
                <div class="value {'positive' if summary['win_rate'] > 0.5 else 'neutral'}">{summary['win_rate']*100:.1f}%</div>
            </div>
            <div class="card">
                <h3>盈亏比</h3>
                <div class="value {'positive' if summary['profit_factor'] > 1 else 'negative'}">{summary['profit_factor']:.2f}</div>
            </div>
        </div>
        
        <h2>📈 权益曲线</h2>
        <div class="chart-container">
            <div style="display: flex; flex-direction: column; gap: 5px;">
"""
    
    # 权益曲线简化展示
    equity_df['equity_pct'] = (equity_df['equity'] / summary['starting_capital'] - 1) * 100
    max_equity = equity_df['equity'].max()
    for i, row in equity_df.iterrows():
        width = (row['equity'] / max_equity) * 100
        color = '#00ff88' if row['equity_pct'] > 0 else '#ff4444'
        if i % 5 == 0:  # 每5个点显示一个
            html += f"""
                <div class="bar">
                    <div class="bar-label">{row['date']}</div>
                    <div class="bar-fill" style="width: {width}%; background: {color};"></div>
                    <div class="bar-value">{row['equity_pct']:.1f}%</div>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <h2>🎯 股票表现</h2>
        <table>
            <thead>
                <tr>
                    <th>股票</th>
                    <th>总盈亏</th>
                    <th>平均盈亏</th>
                    <th>交易次数</th>
                    <th>平均收益率</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for symbol, row in stock_stats.iterrows():
        pnl_class = 'positive' if row['总盈亏'] > 0 else 'negative'
        html += f"""
                <tr>
                    <td>{symbol}</td>
                    <td class="{pnl_class}">¥{row['总盈亏']:,.0f}</td>
                    <td class="{pnl_class}">¥{row['平均盈亏']:,.0f}</td>
                    <td>{int(row['交易次数'])}</td>
                    <td class="{pnl_class}">{row['平均收益率']*100:.2f}%</td>
                </tr>
"""
    
    html += f"""
            </tbody>
        </table>
        
        <h2>📋 最近交易</h2>
        <table>
            <thead>
                <tr>
                    <th>日期</th>
                    <th>类型</th>
                    <th>股票</th>
                    <th>价格</th>
                    <th>数量</th>
                    <th>盈亏</th>
                    <th>原因</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for i, row in trades_df.tail(20).iterrows():
        trade_type = '买入' if row['type'] == 'BUY' else '卖出'
        pnl_class = ''
        pnl_value = ''
        if row['type'] == 'SELL' and pd.notna(row.get('pnl', None)):
            pnl_class = 'positive' if row['pnl'] > 0 else 'negative'
            pnl_value = f"¥{row['pnl']:,.0f} ({row['pnl_rate']*100:.1f}%)"
        
        html += f"""
                <tr>
                    <td>{row.get('date', '-')}</td>
                    <td>{trade_type}</td>
                    <td>{row['symbol']}</td>
                    <td>¥{row['price']:.2f}</td>
                    <td>{int(row['quantity'])}</td>
                    <td class="{pnl_class}">{pnl_value}</td>
                    <td style="font-size: 0.8em; color: #888;">{row.get('reason', '-')[:30]}</td>
                </tr>
"""
    
    html += f"""
            </tbody>
        </table>
        
        <h2>📊 多因子得分分布</h2>
        <div class="chart-container">
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
"""
    
    # 显示最近的因子得分
    recent_factors = factors_df.tail(30)
    for i, row in recent_factors.iterrows():
        score_class = 'positive' if row['score'] > 0.3 else ('negative' if row['score'] < -0.3 else 'neutral')
        html += f"""
                <div style="background: #2a2a2a; padding: 10px; border-radius: 8px; min-width: 150px;">
                    <div style="color: #888; font-size: 0.8em;">{row['date']}</div>
                    <div style="font-weight: bold;">{row['symbol']}</div>
                    <div class="{score_class}">得分: {row['score']:.2f}</div>
                </div>
"""
    
    html += f"""
            </div>
        </div>
        
        <div class="timestamp">
            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            策略: {summary['strategy']} | 总交易次数: {summary['total_trades']}
        </div>
    </div>
</body>
</html>
"""
    
    # 保存 HTML
    output_file = Path(summary_file).parent / f"report_{summary['timestamp']}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 报告已生成: {output_file}")
    return str(output_file)


if __name__ == "__main__":
    import glob
    import sys
    
    # 找到最新的报告文件
    reports_dir = Path(__file__).parent.parent / "reports"
    
    summary_files = sorted(reports_dir.glob("summary_*.json"), reverse=True)
    if not summary_files:
        print("❌ 未找到摘要文件")
        sys.exit(1)
    
    latest = summary_files[0].stem.replace("summary_", "")
    
    summary_file = reports_dir / f"summary_{latest}.json"
    trades_file = reports_dir / f"trades_{latest}.csv"
    factors_file = reports_dir / f"factors_{latest}.csv"
    equity_file = reports_dir / f"equity_curve_{latest}.csv"
    
    print(f"📄 使用报告: {latest}")
    generate_html_report(summary_file, trades_file, factors_file, equity_file)
