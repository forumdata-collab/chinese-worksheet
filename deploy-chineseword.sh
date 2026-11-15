#!/usr/bin/env bash
# 中文筆順練習簿：deploy ~/chinese-worksheet 到 Cloudflare Pages（chineseword.we1co.me）
# 由 Hermes 執行；Muse 只交 zip，不直接發佈。
#
# 2026-11-14：改為先 rsync 去 staging 再上傳。
#   以前 `deploy .` 會連 tools/（48 檔，連 regression.py 都公開）、*.md、docs/*.pdf（1.3MB）
#   一齊上，檔案多又漏開發檔。
set -euo pipefail
cd "$(dirname "$0")"

export $(grep -E '^(CF_ACCOUNT_ID|CF_WORKERS_TOKEN)=' "$HOME/.hermes/.env" | xargs)
export CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-$CF_WORKERS_TOKEN}"
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-$CF_ACCOUNT_ID}"

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
rsync -a \
  --exclude '.git/' --exclude '.gitignore' --exclude '.wrangler/' --exclude '.last-deploy' \
  --exclude 'tools/' --exclude '__pycache__/' --exclude 'node_modules/' \
  --exclude '*.md' --exclude '*.log' --exclude 'docs/*.pdf' \
  ./ "$STAGE"/

OUT=$(npx --no-install wrangler pages deploy "$STAGE" --project-name=chineseword-we1co --branch=main --commit-dirty=true 2>&1) || {
  echo "$OUT" | tail -20; exit 3; }
echo "$OUT" | tail -3

URL=$(echo "$OUT" | grep -oE 'https://[a-z0-9]+\.chineseword-we1co\.pages\.dev' | tail -1)
echo "DEPLOYMENT_URL=$URL"
printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$URL" > .last-deploy

sleep 6
code=$(curl -sL -o /tmp/cw-live.html -w '%{http_code}' https://chineseword.we1co.me/)
title=$(grep -o '<title>[^<]*</title>' /tmp/cw-live.html | head -1)
landing=$(curl -sL -o /dev/null -w '%{http_code}' https://chineseword.we1co.me/landing/)
echo "live http=$code landing=$landing $title"
[ "$code" = "200" ] && [ "$landing" = "200" ] || { echo "VERIFY FAILED（等 5–15 秒再試）"; exit 4; }
echo OK
