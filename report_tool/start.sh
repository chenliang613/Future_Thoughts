#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "已创建 .env 文件，请编辑并填入 ANTHROPIC_API_KEY"
fi

echo "启动行业智能化分析报告工具..."
echo "浏览器访问: http://localhost:8063"
echo "按 Ctrl+C 停止服务"
echo ""

venv/bin/uvicorn app:app --host 0.0.0.0 --port 8063 --reload
