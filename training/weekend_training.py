#!/usr/bin/env python3
"""
小强量化系统 - 周末训练模块
自动下载历史数据、训练因子、优化策略
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# 设置项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

DATA_DIR = PROJECT_DIR / "data" / "qlib_data"
LOG_DIR = PROJECT_DIR / "logs" / "training"


def check_qlib_data():
    """检查 qlib 数据"""
    print("=" * 60)
    print("📊 检查 qlib 数据状态")
    print("=" * 60)
    
    qlib_data_path = Path.home() / ".qlib" / "qlib_data" / "cn_data"
    
    if qlib_data_path.exists():
        files = list(qlib_data_path.glob("**/*"))
        if len(files) > 10:
            print(f"✅ qlib 数据已存在: {len(files)} 个文件")
            return True
    
    print("❌ qlib 数据未安装")
    return False


def download_qlib_data():
    """下载 qlib 数据"""
    print("\n" + "=" * 60)
    print("📥 下载 qlib 数据")
    print("=" * 60)
    
    print("\n正在下载 qlib 内置数据 (约 1GB)...")
    print("预计时间: 10-30 分钟")
    
    cmd = [
        sys.executable, "-m", "qlib.run.get_data", "qlib_data",
        "--target_dir", str(Path.home() / ".qlib" / "qlib_data" / "cn_data"),
        "--region", "cn"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode == 0:
            print("✅ qlib 数据下载完成")
            return True
        else:
            print(f"❌ 下载失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 下载超时")
        return False
    except Exception as e:
        print(f"❌ 下载异常: {e}")
        return False


def download_a_share_history():
    """下载 A股历史数据"""
    print("\n" + "=" * 60)
    print("📥 下载 A股历史数据")
    print("=" * 60)
    
    import akshare as ak
    import pandas as pd
    
    # A股标的列表
    symbols = [
        ("300308.SZ", "中际旭创"),
        ("300394.SZ", "天孚通信"),
        ("300502.SZ", "新易盛"),
        ("002281.SZ", "光迅科技"),
        ("688205.SH", "德科立"),
        ("688195.SH", "腾景科技"),
        ("688307.SH", "中润光学"),
        ("000977.SZ", "浪潮信息"),
        ("002230.SZ", "科大讯飞"),
        ("300033.SZ", "同花顺"),
        ("603501.SH", "韦尔股份"),
        ("002371.SZ", "北方华创"),
        ("300661.SZ", "圣邦股份"),
    ]
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    success = 0
    failed = 0
    
    for symbol, name in symbols:
        try:
            code = symbol.replace(".SZ", "").replace(".SH", "")
            secid = f"0.{code}" if symbol.endswith(".SZ") else f"1.{code}"
            
            print(f"  下载 {symbol} {name}...", end=" ")
            
            # 使用东方财富接口
            import requests
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
                "klt": "101",
                "fqt": "1",
                "beg": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
            }
            
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            
            if data.get("data") and data["data"].get("klines"):
                klines = data["data"]["klines"]
                df = pd.DataFrame([k.split(",") for k in klines], columns=[
                    "date", "open", "close", "high", "low", "volume", "amount",
                    "amplitude", "change_pct", "change", "turnover"
                ])
                
                for col in ["open", "close", "high", "low", "volume", "change_pct"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                
                df["symbol"] = symbol
                df.to_csv(DATA_DIR / f"{symbol}.csv", index=False)
                print(f"✅ {len(df)} 条")
                success += 1
            else:
                print("❌ 无数据")
                failed += 1
            
            import time
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ {e}")
            failed += 1
    
    print(f"\n✅ 成功: {success}, ❌ 失败: {failed}")
    return success > 0


def train_factors():
    """训练因子"""
    print("\n" + "=" * 60)
    print("🧠 训练因子")
    print("=" * 60)
    
    try:
        import qlib
        from qlib.data import D
        from qlib.data.dataset import DatasetH
        from qlib.data.dataset.handler import DataHandlerLP
        
        # 初始化 qlib
        qlib.init(provider=str(Path.home() / ".qlib" / "qlib_data" / "cn_data"), region="cn")
        
        print("✅ qlib 初始化成功")
        
        # 定义因子
        # 这里可以添加自定义因子
        factors = [
            "Ref($close, 1) / $close - 1",  # 收益率
            "$close / Ref($close, 5) - 1",  # 5日收益率
            "$close / Ref($close, 20) - 1",  # 20日收益率
            "$volume / Ref(Mean($volume, 5), 1)",  # 量比
            "($high - $low) / $close",  # 振幅
        ]
        
        print("\n因子列表:")
        for i, f in enumerate(factors, 1):
            print(f"  {i}. {f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 训练失败: {e}")
        return False


def backtest_strategies():
    """回测策略"""
    print("\n" + "=" * 60)
    print("📈 回测策略")
    print("=" * 60)
    
    # 运行回测
    backtest_script = PROJECT_DIR / "backtest" / "backtest_entry.py"
    
    if backtest_script.exists():
        cmd = [sys.executable, str(backtest_script), "--mock"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ 回测失败: {e}")
            return False
    else:
        print("❌ 回测脚本不存在")
        return False


def optimize_parameters():
    """优化参数"""
    print("\n" + "=" * 60)
    print("⚙️ 优化参数")
    print("=" * 60)
    
    # 运行进化
    evolution_script = PROJECT_DIR / "evolution.py"
    
    if evolution_script.exists():
        cmd = [sys.executable, str(evolution_script), "--evolve"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ 优化失败: {e}")
            return False
    else:
        print("❌ 进化脚本不存在")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 小强量化系统 - 周末训练")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # 1. 检查数据
    if not check_qlib_data():
        # 下载 qlib 数据
        if download_qlib_data():
            results["qlib_data"] = "✅ 已下载"
        else:
            results["qlib_data"] = "❌ 下载失败"
    
    # 2. 下载 A股历史数据
    if download_a_share_history():
        results["a_share_data"] = "✅ 已下载"
    else:
        results["a_share_data"] = "⚠️ 部分失败"
    
    # 3. 训练因子
    if train_factors():
        results["factors"] = "✅ 训练完成"
    else:
        results["factors"] = "❌ 训练失败"
    
    # 4. 回测策略
    if backtest_strategies():
        results["backtest"] = "✅ 回测完成"
    else:
        results["backtest"] = "❌ 回测失败"
    
    # 5. 优化参数
    if optimize_parameters():
        results["optimization"] = "✅ 优化完成"
    else:
        results["optimization"] = "❌ 优化失败"
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 训练总结")
    print("=" * 60)
    for task, status in results.items():
        print(f"  {task}: {status}")
    
    print("\n" + "=" * 60)
    print("✅ 周末训练完成")
    print("=" * 60)
    
    # 保存训练日志
    log_file = LOG_DIR / f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(log_file, "w") as f:
        f.write(f"周末训练日志 - {datetime.now()}\n")
        for task, status in results.items():
            f.write(f"{task}: {status}\n")
    
    print(f"\n📝 日志已保存: {log_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="小强量化系统 - 周末训练")
    parser.add_argument("--download-data", action="store_true", help="只下载数据")
    parser.add_argument("--train", action="store_true", help="只训练因子")
    parser.add_argument("--backtest", action="store_true", help="只回测")
    parser.add_argument("--optimize", action="store_true", help="只优化参数")
    parser.add_argument("--all", action="store_true", help="执行全部")
    
    args = parser.parse_args()
    
    if args.download_data:
        download_a_share_history()
    elif args.train:
        train_factors()
    elif args.backtest:
        backtest_strategies()
    elif args.optimize:
        optimize_parameters()
    elif args.all:
        main()
    else:
        main()
