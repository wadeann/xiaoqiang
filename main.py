#!/usr/bin/env python3
"""
CEO Agent - Qlib Evolution Integrated XiaoQiang System v2
支持 mode/action 参数的增强版
"""

import sys
import subprocess
import logging
import json
import argparse
import urllib.request
from pathlib import Path
from datetime import datetime

# 全局logger
logger = logging.getLogger(__name__)

class QlibIntegratedXiaoQiang:
    """CEO agent with mandatory Qlib Evolution integration"""

    def __init__(self):
        self.qlib_required = True
        self.qlib_threshold = 0.0089  # From Qlib config
        self.logger = logging.getLogger(__name__)
        self.log_dir = Path("/home/wade/.openclaw/logs/ceo")
        self.log_dir.mkdir(exist_ok=True)

    def analyze_stock(self, symbol):
        """Analyze stock with mandatory Qlib Evolution check"""
        try:
            logger.info(f"Starting CEO analysis for {symbol}")

            # Must check Qlib Evolution first
            qlib_score = self._get_qlib_evolution_score(symbol)

            if qlib_score < self.qlib_threshold:
                logger.info(f"{symbol} rejected: Qlib score {qlib_score:.6f} below threshold {self.qlib_threshold}")
                return {
                    'symbol': symbol,
                    'status': 'REJECTED',
                    'reason': f'Below Qlib Evolution threshold ({self.qlib_threshold})',
                    'qlib_score': qlib_score
                }

            logger.info(f"{symbol} passed Qlib threshold: {qlib_score:.6f}")

            # Only proceed with Rockflow API trading if Qlib passes
            result = self._execute_rockflow_analysis(symbol, qlib_score)

            return {
                'symbol': symbol,
                'status': 'ANALYZED',
                'qlib_score': qlib_score,
                'rockflow_result': result
            }

        except Exception as e:
            logger.error(f"CEO analysis failed for {symbol}: {e}")
            return {
                'symbol': symbol,
                'status': 'ERROR',
                'error': str(e)
            }

    def _get_qlib_evolution_score(self, symbol):
        """Unified interface to Qlib Evolution"""
        try:
            result = subprocess.run([
                '/home/wade/.openclaw/qlib_evolution/venv/bin/python',
                '/home/wade/.openclaw/qlib_evolution/single_analyze.py',
                symbol.lower()
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise Exception(f"Qlib Evolution unavailable for {symbol}: {result.stderr}")

            score = float(result.stdout.strip())
            logger.debug(f"QLIB score for {symbol}: {score}")
            return score

        except Exception as e:
            logger.error(f"Failed to get Qlib Evolution score for {symbol}: {e}")
            raise

    def _execute_rockflow_analysis(self, symbol, qlib_score):
        """Execute Rockflow API analysis (only if Qlib passes)"""
        try:
            analysis_result = {
                'symbol': symbol,
                'qlib_validation_passed': qlib_score >= self.qlib_threshold,
                'technical_signals': self._generate_technical_signals(symbol),
                'risk_assessment': self._assess_risk(symbol, qlib_score),
                'trading_recommendation': self._generate_trading_recommendation(qlib_score)
            }

            self._log_rockflow_decision(symbol, qlib_score, analysis_result)
            return analysis_result

        except Exception as e:
            logger.error(f"Rockflow analysis failed for {symbol}: {e}")
            return {'error': str(e)}

    def _generate_technical_signals(self, symbol):
        """Generate technical analysis signals"""
        return {
            'rsi': 65.2,
            'macd_signal': 'bullish',
            'moving_average_alignment': 'positive',
            'volume_profile': 'normal'
        }

    def _assess_risk(self, symbol, qlib_score):
        """Assess risk level based on Qlib score"""
        risk_level = 'LOW'
        if qlib_score < 0.001:
            risk_level = 'HIGH'
        elif qlib_score < 0.005:
            risk_level = 'MEDIUM'

        return {
            'level': risk_level,
            'position_size_limit': '3%' if risk_level == 'LOW' else '1%',
            'stop_loss': '-10%' if risk_level == 'LOW' else '-5%',
            'take_profit': '+20%' if risk_level == 'LOW' else '+10%'
        }

    def _generate_trading_recommendation(self, qlib_score):
        """Generate trading recommendation based on Qlib score"""
        if qlib_score >= 0.01:
            return 'BUY_STRONG'
        elif qlib_score >= 0.0012:
            return 'BUY_WEAK'
        elif qlib_score <= -0.0012:
            return 'SELL'
        else:
            return 'HOLD'

    def _log_rockflow_decision(self, symbol, qlib_score, result):
        """Log Rockflow decision for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'qlib_score': qlib_score,
            'threshold': self.qlib_threshold,
            'qualified': qlib_score >= self.qlib_threshold,
            'recommendation': result.get('trading_recommendation', 'UNKNOWN'),
            'risk_level': result.get('risk_assessment', {}).get('level', 'UNKNOWN')
        }

        log_file = self.log_dir / "rockflow_decisions.json"
        try:
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []

            logs.append(log_entry)
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to log Rockflow decision: {e}")


class MarketScanner:
    """市场扫描器 - 支持A股和美股扫描"""

    def __init__(self):
        self.watchlist_file = Path("/home/wade/.openclaw/qlib_evolution/shared/vip_watchlist.json")
        self.name_map_file = Path("/home/wade/.openclaw/qlib_evolution/shared/stock_name_map.json")
        self.scores_file = Path("/home/wade/.openclaw/qlib_evolution/shared/latest_scores.json")
        self.xiaoqiang = QlibIntegratedXiaoQiang()

    def load_watchlist(self):
        """加载监控列表"""
        try:
            if self.watchlist_file.exists():
                with open(self.watchlist_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load watchlist: {e}")
        return {}

    def load_name_map(self):
        """加载股票名称映射"""
        try:
            if self.name_map_file.exists():
                with open(self.name_map_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load name map: {e}")
        return {}

    def load_scores(self):
        """加载最新评分"""
        try:
            if self.scores_file.exists():
                with open(self.scores_file, 'r') as f:
                    data = json.load(f)
                    return data.get('scores', {})
        except Exception as e:
            logger.error(f"Failed to load scores: {e}")
        return {}

    def a_share_pre_market(self):
        """A股盘前扫描"""
        logger.info("=" * 50)
        logger.info("📊 A股盘前扫描启动")
        logger.info("=" * 50)

        watchlist = self.load_watchlist()
        scores = self.load_scores()
        name_map = self.load_name_map()

        # 获取监控池中的高评分股票
        monitored_codes = list(watchlist.keys())[:20]  # 前20只

        results = []
        for code in monitored_codes:
            score = scores.get(code, 0)
            if score >= 0.001:  # 只关注有意义的评分
                name = name_map.get(code, code)
                results.append({
                    'code': code,
                    'name': name,
                    'score': score,
                    'signal': 'STRONG_BUY' if score >= 0.01 else 'BUY' if score >= 0.0012 else 'HOLD'
                })

        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"✅ 盘前扫描完成，发现 {len(results)} 只高评分标的")
        for r in results[:5]:
            logger.info(f"  {r['name']}({r['code']}): {r['score']:.4f} - {r['signal']}")

        return results

    def a_share_scan(self):
        """A股盘中扫描"""
        logger.info("=" * 50)
        logger.info("🔍 A股盘中扫描启动")
        logger.info("=" * 50)

        scores = self.load_scores()
        name_map = self.load_name_map()

        # 获取评分最高的前10只
        top_stocks = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]

        results = []
        for code, score in top_stocks:
            if score >= 0.001:
                name = name_map.get(code, code)
                results.append({
                    'code': code,
                    'name': name,
                    'score': score,
                    'signal': 'STRONG_BUY' if score >= 0.01 else 'BUY' if score >= 0.0012 else 'HOLD'
                })

        logger.info(f"✅ 盘中扫描完成，TOP 10 标的:")
        for r in results:
            logger.info(f"  {r['name']}({r['code']}): {r['score']:.4f}")

        return results

    def a_share_opportunity(self):
        """A股遗漏机会扫描 - 收盘前检查"""
        logger.info("=" * 50)
        logger.info("🎯 A股遗漏机会扫描")
        logger.info("=" * 50)

        watchlist = self.load_watchlist()
        scores = self.load_scores()
        name_map = self.load_name_map()

        # 监控池中评分高但可能错过的机会
        opportunities = []
        for code in watchlist:
            score = scores.get(code, 0)
            if score >= 0.005:  # 高评分
                name = name_map.get(code, code)
                opportunities.append({
                    'code': code,
                    'name': name,
                    'score': score,
                    'type': 'MISSED_OPPORTUNITY'
                })

        opportunities.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"⚠️ 发现 {len(opportunities)} 只可能的遗漏机会")
        for opp in opportunities[:5]:
            logger.info(f"  {opp['name']}({opp['code']}): {opp['score']:.4f}")

        return opportunities

    def a_share_post_market(self):
        """A股盘后总结"""
        logger.info("=" * 50)
        logger.info("🏁 A股盘后总结启动")
        logger.info("=" * 50)

        watchlist = self.load_watchlist()
        scores = self.load_scores()
        name_map = self.load_name_map()

        # 复盘今日表现（简单逻辑：按评分排名前10的标的）
        summary = []
        top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]

        for code, score in top_scores:
            name = name_map.get(code, code)
            summary.append({
                'code': code,
                'name': name,
                'final_score': score,
                'status': 'REVIEWED'
            })

        logger.info(f"✅ 盘后总结完成，今日核心标的 {len(summary)} 只")
        for s in summary[:5]:
            logger.info(f"  {s['name']}({s['code']}): 最终评分 {s['final_score']:.4f}")

        return summary

    def us_share_scan(self):
        """美股扫描"""
        logger.info("=" * 50)
        logger.info("🇺🇸 美股扫描启动")
        logger.info("=" * 50)

        # 美股监控列表（示例）
        us_watchlist = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMD', 'PLTR']

        results = []
        for symbol in us_watchlist:
            # 美股暂用模拟评分
            try:
                # 这里可以接入美股数据源
                score = 0.001  # 占位符
                results.append({
                    'code': symbol,
                    'name': symbol,
                    'score': score,
                    'signal': 'MONITOR'
                })
            except Exception as e:
                logger.warning(f"美股 {symbol} 扫描失败: {e}")

        logger.info(f"✅ 美股扫描完成，监控 {len(results)} 只标的")
        return results

    def us_share_trade(self):
        """美股交易检查 - 深夜运行"""
        logger.info("=" * 50)
        logger.info("🌙 美股交易时段检查")
        logger.info("=" * 50)

        # 检查美股市场状态
        now = datetime.now()
        logger.info(f"当前时间: {now}")

        # 美股交易时间：美东时间 09:30-16:00
        # 北京时间：夏令时 21:30-04:00，冬令时 22:30-05:00

        results = self.us_share_scan()

        # 分析交易机会
        trade_signals = []
        for stock in results:
            if stock['score'] >= 0.005:
                trade_signals.append(stock)

        logger.info(f"✅ 发现 {len(trade_signals)} 只交易信号")
        return trade_signals


def main():
    """Main entry point for CEO agent"""
    parser = argparse.ArgumentParser(description='CEO Agent - Qlib Evolution Integrated XiaoQiang System v2')

    # 原有参数
    parser.add_argument('--analyze', type=str, help='Stock symbol to analyze')
    parser.add_argument('--batch', nargs='+', help='List of symbols to analyze')

    # 新增 mode/action 参数
    parser.add_argument('--mode', type=str, choices=['a_share', 'us_share'],
                        help='Market mode: a_share (A股) or us_share (美股)')
    parser.add_argument('--action', type=str,
                        choices=['pre_market', 'scan', 'opportunity', 'trade', 'post_market'],
                        help='Action to perform')

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 如果使用了 mode 和 action 参数
    if args.mode and args.action:
        scanner = MarketScanner()

        if args.mode == 'a_share':
            if args.action == 'pre_market':
                results = scanner.a_share_pre_market()
                print(json.dumps({'mode': 'a_share', 'action': 'pre_market', 'results': results}, indent=2, ensure_ascii=False))

            elif args.action == 'scan':
                results = scanner.a_share_scan()
                print(json.dumps({'mode': 'a_share', 'action': 'scan', 'results': results}, indent=2, ensure_ascii=False))

            elif args.action == 'opportunity':
                results = scanner.a_share_opportunity()
                print(json.dumps({'mode': 'a_share', 'action': 'opportunity', 'results': results}, indent=2, ensure_ascii=False))

            elif args.action == 'post_market':
                results = scanner.a_share_post_market()
                print(json.dumps({'mode': 'a_share', 'action': 'post_market', 'results': results}, indent=2, ensure_ascii=False))

        elif args.mode == 'us_share':
            if args.action == 'scan':
                results = scanner.us_share_scan()
                print(json.dumps({'mode': 'us_share', 'action': 'scan', 'results': results}, indent=2, ensure_ascii=False))

            elif args.action == 'trade':
                results = scanner.us_share_trade()
                print(json.dumps({'mode': 'us_share', 'action': 'trade', 'results': results}, indent=2, ensure_ascii=False))

    # 如果使用了原有参数
    elif args.analyze:
        trader = QlibIntegratedXiaoQiang()
        result = trader.analyze_stock(args.analyze)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.batch:
        trader = QlibIntegratedXiaoQiang()
        results = {}
        for symbol in args.batch:
            results[symbol] = trader.analyze_stock(symbol)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    else:
        print("Usage:")
        print("  --mode a_share --action pre_market    A股盘前扫描")
        print("  --mode a_share --action scan          A股盘中扫描")
        print("  --mode a_share --action opportunity   A股遗漏机会")
        print("  --mode us_share --action scan         美股扫描")
        print("  --mode us_share --action trade        美股交易检查")
        print("  --analyze SYMBOL                      分析单只股票")
        print("  --batch SYM1 SYM2                     批量分析")


if __name__ == "__main__":
    main()
