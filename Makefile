.PHONY: install dev backend frontend build clean reset-data

# 一条命令：装依赖、起前后端、自检端口与数据
dev:
	python3 scripts/dev.py

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && ./run.sh

frontend:
	cd frontend && npm run dev

# 构建前端产物到 frontend/dist（后端检测到 dist 会自动托管，与本地数据互不干扰）
build:
	cd frontend && npm run build

# 只清理构建产物，不动本地数据与依赖
clean:
	rm -rf frontend/dist

# 重置本地示例数据：停掉服务后执行，下次启动会重新播种
reset-data:
	rm -f backend/data/app.db
