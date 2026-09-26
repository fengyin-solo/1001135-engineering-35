.PHONY: install dev backend frontend smoke build clean reset

# 装依赖：前后端一起装，失败时给出可读说明并允许重试
install:
	bash scripts/install.sh

# 本地一条链：装依赖 → 起后端（端口自检/顺延）→ 数据自检 → 起前端
dev:
	bash scripts/dev.sh

# 只起后端（端口被占用时自动顺延并打印）
backend:
	cd backend && ./run.sh

# 只起前端（需后端已在运行；代理目标可用 VITE_PROXY_TARGET 覆盖）
frontend:
	cd frontend && npm run dev

# 数据自检：以 .runtime 里记录的实际端口为准，缺省 8000
smoke:
	@PORT=$$(cat backend/.runtime/backend.port 2>/dev/null || echo 8000); \
	backend/.venv/bin/python scripts/smoke.py "http://127.0.0.1:$$PORT"

# 构建：产物只落在 frontend/dist 与 __pycache__，不碰本地运行数据
build:
	cd frontend && npm run build
	backend/.venv/bin/python -m compileall -q backend/app
	@echo "构建完成：前端产物在 frontend/dist/，与本地运行互不影响"

# 清理构建产物与运行期临时文件（保留本地数据）
clean:
	rm -rf frontend/dist backend/.runtime
	find backend/app -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

# 清空本地数据：下次启动重新生成示例数据
reset:
	rm -f backend/data/app.sqlite3 backend/data/app.sqlite3-wal backend/data/app.sqlite3-shm
	@echo "本地数据已清空，下次启动将重新生成示例数据"
