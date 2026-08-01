#!/bin/bash
# 启动本地开发服务器
# 用法：bash scripts/start-server.sh [port]
# 默认端口 8000

PORT=${1:-8000}
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$DIR" || exit 1

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  个人记账 + 家庭台账 本地服务器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  目录：$DIR"
echo "  端口：$PORT"
echo ""
echo "  本机访问：http://localhost:$PORT/"
echo "  手机访问：http://$(ipconfig getifaddr en0 2>/dev/null || echo '<UNKNOWN>'):$PORT/"
echo "  （手机需与 Mac 同 WiFi）"
echo ""
echo "  按 Ctrl+C 停止"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 -m http.server "$PORT"
