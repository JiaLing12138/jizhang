#!/bin/bash
# 一键发布到 GitHub Pages
# 用法：bash scripts/publish.sh
set -e
cd "$(dirname "$0")/.."
git add -A
git diff --cached --quiet || git commit -m "更新页面 $(date '+%Y-%m-%d %H:%M')"
echo "→ 推送到 GitHub..."
git push origin main
echo "→ 刷新 CDN 缓存..."
curl -sS -m 20 "https://purge.jsdelivr.net/gh/JiaLing12138/jizhang@main/personal.html" >/dev/null || true
curl -sS -m 20 "https://purge.jsdelivr.net/gh/JiaLing12138/jizhang@main/index.html" >/dev/null || true
curl -sS -m 20 "https://purge.jsdelivr.net/gh/JiaLing12138/jizhang@main/shortcuts/%E8%AE%B0%E8%B4%A6OCR.shortcut" >/dev/null || true
curl -sS -m 20 "https://purge.jsdelivr.net/gh/JiaLing12138/jizhang@main/shortcuts/%E8%AE%B0%E8%B4%A6OCR%E8%B1%86%E5%8C%85.shortcut" >/dev/null || true
curl -sS -m 20 "https://purge.jsdelivr.net/gh/JiaLing12138/jizhang@main/shortcuts/%E8%AE%B0%E8%B4%A6OCR%E8%B1%86%E5%8C%85-%E8%B0%83%E8%AF%95.shortcut" >/dev/null || true
echo "✅ 已发布：https://gcore.jsdelivr.net/gh/JiaLing12138/jizhang@main/personal.html（约 1 分钟内生效）"
