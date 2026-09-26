# 港口集装箱作业调度平台

面向船舶靠泊、集装箱装卸、堆场堆存、闸口进出与理货结算的一体化港口作业调度后台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 环境要求

- Python 3.11+（后端依赖版本已锁定在 `backend/requirements.txt`）
- Node.js 20+（前端依赖版本锁定在 `frontend/package-lock.json`）

## 一条命令跑起来

```bash
make dev        # 等价于 python3 scripts/dev.py
```

这条命令会依次完成：

1. **装依赖**：后端建 `.venv` 并 `pip install`，前端 `npm install`。
   装不上时会打印可能的原因（网络/代理/镜像源、Python 或 Node 版本）并询问是否重试；
   安装是幂等的，修好后重跑命令也可以。
2. **探端口**：后端从 8000、前端从 5173 开始探测，被占用就顺延到下一个可用端口，
   实际使用的端口会打印出来（前端代理会自动指向实际的后端端口）。
3. **起服务并自检**：同时拉起前后端，等后端 `/api/health` 通过后打印访问地址与数据概况。
   `Ctrl+C` 一次停掉两个进程。

启动后打开终端里打印的前端地址（默认 `http://127.0.0.1:5173/`）即可看到页面，
运营概览的数字来自同一份数据文件，与各模块列表一致。

## 本地数据

- 数据放在 SQLite 文件 `backend/data/app.db`（可用环境变量 `APP_DB_PATH` 改位置）。
- 首次启动自动灌入示例数据；**重复起服务不会重复塞数**——某个模块已有数据就跳过。
- 想重置数据：停掉服务后执行 `make reset-data`（或手动删掉数据文件），下次启动重新播种。
- 数据文件与前端构建产物 `frontend/dist` 分属两棵目录树，互不影响。

## 构建产物

```bash
make build      # 前端构建到 frontend/dist
make clean      # 只删构建产物，不动数据与依赖
```

`frontend/dist` 存在时，后端会直接托管它（未匹配的 GET 路径回退到 `index.html`，
刷新不会 404），此时访问后端地址即可打开页面；dev server 与构建产物读同一份数据，
两种打开方式看到的数字一致。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   ├── app/store.py          SQLite 数据仓库（读缓存、写落盘）
│   ├── app/ports.py          端口探测（被占用时顺延）
│   └── data/                 本地数据文件（首次启动自动生成）
├── scripts/dev.py            一条命令的本地启动链
├── .env.example              可调的环境变量说明
└── docker-compose.yml
```

## 分开启动（调试单个服务时用）

### 后端

```bash
cd backend && ./run.sh
```

`run.sh` 会装依赖、探测端口（8000 被占用就顺延并打印）后起服务。
健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端，后端端口不是 8000 时用
`VITE_PROXY_TARGET=http://127.0.0.1:<端口> npm run dev` 指定。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 泊位计划 | `berth` | 泊位计划 | 计划编号、泊位编号、靠泊船舶 |
| 船舶档案 | `vessel` | 船舶 | 船舶编号、船舶名称、船舶类型 |
| 航次管理 | `voyage` | 航次 | 航次编号、关联船舶、进口航次号 |
| 岸桥作业 | `crane` | 岸桥 | 设备编号、岸桥型号、额定起重量 |
| 装卸任务 | `loading` | 装卸任务 | 任务编号、关联航次、作业类型 |
| 堆场管理 | `yard` | 箱区 | 箱区编号、箱区名称、堆放层数 |
| 集装箱档案 | `container` | 集装箱 | 箱号、箱型、箱况等级 |
| 堆存记录 | `yardstore` | 堆存单 | 堆存单号、关联箱号、箱区编号 |
| 闸口通行 | `gate` | 通行记录 | 通行编号、车牌号码、关联箱号 |
| 集卡调度 | `truck` | 集卡 | 调度单号、集卡牌号、司机姓名 |
| 理货作业 | `tally` | 理货单 | 理货单号、关联航次、理货方式 |
| 残损登记 | `damage` | 残损记录 | 残损编号、关联箱号、残损类型 |
| 单证处理 | `manifest` | 单证 | 单证编号、单证类型、关联航次 |
| 堆存计费 | `storage` | 计费单 | 计费单号、关联箱号、计费周期 |
| 引航拖轮 | `pilot` | 引航作业 | 作业编号、作业类型、关联船舶 |
| 安全监督 | `safety` | 安全检查 | 检查编号、检查区域、检查类型 |
| 货主档案 | `customer` | 货主 | 客户编码、客户名称、客户类型 |
| 作业结算 | `settle` | 结算单 | 结算单号、结算对象、结算周期 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。
- 数据读写统一走 `app/store.py`：读用 `rows`/`find`，写用 `add`/`save`（写会同步落盘）。
