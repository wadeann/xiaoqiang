#!/bin/bash
cd /home/wade/.openclaw/agents/ceo/workspace/xiaoqiang
source venv/bin/activate
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/c4117646-3e33-4023-a248-d91baa0d921d"
python push_report.py --mode a_share
