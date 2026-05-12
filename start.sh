#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=/home/rxshi/soft/deepmd-kit/envs/marx/bin/python

# 端口配置（默认 8000，可通过参数或环境变量指定）
PORT="${1:-${BACKEND_PORT:-8000}}"

# 环境设置
unset ALL_PROXY all_proxy
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-sk-da8f7c9812754645ae7e83971556e458}"

echo "=== 启动 Marx AI ==="

# 写入前端环境配置
echo "NEXT_PUBLIC_API_URL=http://localhost:${PORT}" > "$DIR/web/.env.local"

# 启动后端
echo "[1/2] 启动后端 (http://localhost:${PORT})..."
$PYTHON "$DIR/server/main.py" --port "$PORT" &
BACKEND_PID=$!

# 等待后端就绪
echo "  等待后端加载模型..."
for i in $(seq 1 60); do
    if curl -s "http://localhost:${PORT}/api/health" > /dev/null 2>&1; then
        echo "  后端就绪"
        break
    fi
    sleep 1
done

# 启动前端
echo "[2/2] 启动前端 (http://localhost:3000)..."
cd "$DIR/web"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "==================================="
echo "  Marx AI 已启动"
echo "  前端: http://localhost:3000"
echo "  API:  http://localhost:${PORT}/docs"
echo "  按 Ctrl+C 停止所有服务"
echo "==================================="

cleanup() {
    echo ""
    echo "正在停止..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait
    echo "已停止"
}
trap cleanup EXIT INT TERM

wait
