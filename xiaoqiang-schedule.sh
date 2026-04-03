#!/bin/bash
# 小强定时任务配置
# 
# 安装方法:
# crontab -e
# 然后添加以下行:

# 早间 A股盘前分析 (北京时间 08:00)
0 8 * * 1-5 cd /home/wade/.openclaw/agents/ceo/workspace/xiaoqiang && source venv/bin/activate && python daily_workflow.py --mode morning >> logs/morning.log 2>&1

# 晚间抓龙行动 - 美股开盘前扫描 (北京时间 21:00)
0 21 * * 1-5 cd /home/wade/.openclaw/agents/ceo/workspace/xiaoqiang && source venv/bin/activate && python daily_workflow.py --mode evening >> logs/evening.log 2>&1

# 每日收盘汇报 - 美股收盘后 (北京时间 06:00，次日凌晨)
0 6 * * 2-6 cd /home/wade/.openclaw/agents/ceo/workspace/xiaoqiang && source venv/bin/activate && python daily_workflow.py --mode report >> logs/report.log 2>&1

# 说明:
# - 早间分析: 周一至周五 08:00
# - 晚间抓龙: 周一至周五 21:00 (美股开盘前)
# - 每日汇报: 周二至周六 06:00 (美股收盘后)
