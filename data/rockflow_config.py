# 小强量化系统配置
# 从 config.yaml 中读取

import yaml
from pathlib import Path

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"

def load_config():
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

# 加载配置
_config = load_config()

# API 配置
API_KEY = _config.get("api", {}).get("rockflow", {}).get(
    "api_key",
    "rk2.paper.eyJraWQiOiJha19tMnVzZWZkYnFoMWZnMG5xIiwiZXhwIjoxNzc3NTgzNDA1fQ.iZdP7wZysHn7xn3rZT7Gw01fzG7XFdFTvWrBklhcFHI"
)
BASE_URL = _config.get("api", {}).get("rockflow", {}).get(
    "base_url",
    "https://paper-mcp.rockflow.tech/bot/api/http_gateway/v1"
)

# 交易配置
STARTING_CAPITAL = _config.get("trading", {}).get("starting_capital", 1000000)
TARGET_RETURN = _config.get("trading", {}).get("target_return", 1.0)
STOP_LOSS = _config.get("trading", {}).get("stop_loss", -0.10)

# 标的配置
US_TICKERS = _config.get("tickers", {}).get("us", [
    "NVDA", "TSLA", "ARM", "ASML", "PLTR", "MU", "TSM", "CRWV", "IREN", "NBIS", "BABA", "BIDU"
])
HK_TICKERS = _config.get("tickers", {}).get("hk", [
    "00700.HK", "09988.HK", "09888.HK", "00981.HK", "02513.HK", "06869.HK", "00100.HK"
])

# A股标的 (从新配置结构读取)
A_SHARE_CONFIG = _config.get("tickers", {}).get("a_share", {})

# 扁平化 A股标的列表
A_SHARE_TICKERS = []
for category, tickers in A_SHARE_CONFIG.items():
    if isinstance(tickers, list):
        A_SHARE_TICKERS.extend(tickers)

# 如果新配置为空，使用默认列表
if not A_SHARE_TICKERS:
    A_SHARE_TICKERS = [
        # AI 芯片
        "300474.SZ",  # 景嘉微
        "688981.SH",  # 中芯国际
        "002049.SZ",  # 紫光国微
        # 光模块/光通信
        "300308.SZ",  # 中际旭创
        "300394.SZ",  # 天孚通信
        "300502.SZ",  # 新易盛
        "002281.SZ",  # 光迅科技
        # AI 算力
        "000977.SZ",  # 浪潮信息
        "002230.SZ",  # 科大讯飞
        "300033.SZ",  # 同花顺
        # 半导体
        "603501.SH",  # 韦尔股份
        "002371.SZ",  # 北方华创
        "300661.SZ",  # 圣邦股份
        # 新能源
        "300750.SZ",  # 宁德时代
        "002594.SZ",  # 比亚迪
    ]

if __name__ == "__main__":
    print("小强量化系统配置:")
    print(f"  API Base URL: {BASE_URL}")
    print(f"  起始资金: ${STARTING_CAPITAL:,.0f}")
    print(f"  目标收益: {TARGET_RETURN*100}%")
    print(f"  止损线: {STOP_LOSS*100}%")
    print(f"  美股标的: {US_TICKERS}")
    print(f"  港股标的: {HK_TICKERS}")
    print(f"  A股标的: {A_SHARE_TICKERS}")
