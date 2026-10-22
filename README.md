# Project_Register 项目台账系统

> 一个项目一本账：覆盖前向签约立项、后向采购实施、交付验收全流程，含过程性资料与履约资料按环节归档。

## 快速开始（一键启动）

```powershell
.\start.ps1
```

自动完成：依赖安装（首次）→ 后端 `8100` → 前端 `3000`（代理 /api）→ 打开浏览器 `http://localhost:3000`。

> 端口说明：后端使用 **8100**（本机 8000 已被 BidAlert 占用）；前端 Vite dev 固定 3000。

## 手动启动

```powershell
# 后端
cd backend
D:\developTools\python\python3.14.5\python.exe -X utf8 -m uvicorn app.main:app --port 8100

# 前端（另开终端）
cd frontend
npm install   # 首次
npm run dev
```

- 前端：<http://localhost:3000>
- 后端 API 文档：<http://127.0.0.1:8100/docs>

## 核心概念（详见 CONTEXT.md）

- **固定生命周期 9 阶段**：商机 → 中标 → 签约 → 立项 → 采购 → 实施 → 交付 → 验收 → 结算
- **存量项目任意阶段起步**：起始阶段之前的阶段标记"存量未纳入"
- **阶段锚点树**：每项目自动生成 9 个锚点作为归档树顶层，子环节任意嵌套，附件挂任意层级
- **当前阶段独立流转**：可推进/回退/跳转并留痕，与资料树互不影响
- **采购单/验收记录**：项目平级明细（1 对多），三口径金额的唯一来源
- **三口径统计**：前向=签约额、后向=Σ采购单、交付=Σ验收回款，只算不存，支持 Excel 导出

## 数据与备份

- 数据库：`backend/data/ledger.db`（SQLite）
- 附件目录：`backend/data/uploads/{project_id}/`（物理名为 uuid，原名存元数据）
- **备份 = 整体拷贝 `backend/data/` 目录**（均已排除出版本库）

## 技术栈

FastAPI + SQLAlchemy + SQLite ｜ Vue3 + Vite + Element Plus ｜ 个人工具（本机运行，无需登录）

## 测试

```powershell
cd backend
D:\developTools\python\python3.14.5\python.exe -X utf8 -m pytest tests -v
```

## 开发状态

- [x] 阶段 0：项目初始化
- [x] 阶段 1：需求（头脑风暴 / PRD / 需求拆分）
- [x] 阶段 2：设计（领域模型 / ADR / 架构设计）
- [x] 阶段 3：技术规格与原型验证
- [x] 阶段 4：开发计划与任务拆分（13 任务）
- [x] 阶段 5：编码实现（TDD，29 项后端测试全绿 + 三页面浏览器验证）
- [ ] 阶段 6：交付与交接

## 文档索引

| 文档 | 路径 |
|------|------|
| 头脑风暴记录 | `docs/brainstorming/` |
| 产品需求文档（PRD） | `tasks/prd-project-ledger.md` |
| 需求拆分 | `docs/requirements/` |
| 领域术语表 | `CONTEXT.md` |
| 架构决策记录 | `docs/adr/`（4 条） |
| 架构设计 | `docs/specs/2026-10-22-architecture-design.md` |
| 技术规格 | `docs/specs/2026-10-22-technical-spec.md` |
| 原型验证 | `docs/specs/2026-10-22-prototype-validation.md`（逻辑原型分支 `prototype/ledger-logic-v1`） |
| 开发计划 | `docs/plans/2026-10-22-project-ledger-plan.md` |
