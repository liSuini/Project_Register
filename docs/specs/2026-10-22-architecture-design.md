# 架构设计：项目台账系统

> 日期：2026-10-22 ｜ 上游：PRD v0.1、CONTEXT.md、ADR 0001-0004

## 1. 总体架构

```
┌─────────────────────────────────────────────────────┐
│  frontend/  Vue3 + Vite + Element Plus (SPA)        │
│    列表页 · 详情页(一账制) · 统计页                   │
└────────────────── REST/JSON ────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  backend/   FastAPI                                  │
│  ┌───────── 薄适配层：api/ 路由 ─────────┐            │
│  │                                      │            │
│  ├─ 深模块层：services/ ─────────────────┤            │
│  │  project_service   tree_service      │            │
│  │  stats_service     storage           │            │
│  └──────────────────────────────────────┘            │
│  models/ (SQLAlchemy)  schemas/ (Pydantic)           │
├─────────────────────────────────────────────────────┤
│  SQLite (data/ledger.db) + 文件系统 (data/uploads/)   │
└─────────────────────────────────────────────────────┘
```

**分层原则**：`api/` 路由是薄适配层（参数校验后直接委托）；全部行为藏在 `services/` 深模块后。测试主要打在 service 接口上（接口即测试面），api 层做少量集成冒烟。

## 2. 模块设计（接口与实现分离）

### 2.1 storage（附件存储）——真正的 seam

| 接口 | 说明 |
|------|------|
| `save(upload_file, project_id) -> StoredFile` | 存入文件，返回 {original_name, stored_path, size, mime} |
| `open_path(stored_path) -> Path` | 返回可读文件路径（供 FileResponse 下载） |
| `remove(stored_path) -> None` | 删除物理文件（容忍已不存在） |

- 实现复杂度全部藏在内部：路径规则（`uploads/{project_id}/{uuid}{ext}`）、大小/MIME 识别、安全文件名清洗。
- 两个 adapter：`LocalFilesystemStorage`（生产，根目录来自配置）；测试注入临时目录的同一 adapter。附件表 `attachments` 挂在其之上，仅存元数据（ADR-0003）。
- **删除校验测试**：通过 service 接口测"删附件→物理文件也删"与"记录删了文件不在→不报错"两条路径。

### 2.2 tree_service（环节树）

| 接口 | 说明 |
|------|------|
| `create_project_tree(project_id)` | 建 9 个阶段锚点（随项目创建自动调用） |
| `get_tree(project_id) -> NodeTree` | 一次查询整树（含各节点附件计数），返回已组装的树形结构 |
| `add_node(parent_id, name) -> Node` | 在任意节点下加子环节 |
| `rename_node(node_id, name)` | 重命名子环节（锚点不可改名） |
| `delete_node(node_id)` | 删除子环节（见下行约束） |

- 内藏实现：递归装配、锚点不可删改的保护、跨项目 parent 校验（parent 与子节点必须同 project_id）。
- **删除约束（业务规则）**：有子节点或有附件的节点禁止删除，需先清空——防止误删整棵子树连带资料，前端给明确提示。锚点永不删除。
- 深度体现：调用方（api/前端）只说"加/删/改名"，全然不知递归与保护规则。

### 2.3 project_service（项目 + 阶段）

| 接口 | 说明 |
|------|------|
| `create(data) -> Project` | 建项目（任选起始阶段），自动调 tree_service 建锚点 |
| `search(keyword, stage) -> list` | 按名称模糊 + 当前阶段筛选 |
| `update(project_id, data)` | 编辑项目基本信息 |
| `change_stage(project_id, target_stage)` | 推进/回退阶段，写 stage_history |
| `get_detail(project_id) -> LedgerDetail` | 详情页聚合：项目+树+采购+验收+附件，一次取全"一本账" |

- 阶段集合（9 个）在此模块内常量定义，change_stage 校验 target 合法性；回退同样允许（ADR-0002：状态独立于树）。
- `get_detail` 是"一账制"的杠杆点：前端详情页一个请求拿全，避免 4 次 round-trip。

### 2.4 stats_service（三口径统计 + 导出）

| 接口 | 说明 |
|------|------|
| `calibers() -> CaliberSummary` | 三口径卡片：各口径项目数+金额（签约额=Σprojects.contract_amount；采购额=Σpurchase_orders.amount；回款额=Σacceptance_records.received_amount） |
| `export_xlsx() -> bytes` | 三口径明细导出（openpyxl：三 sheet） |

- 金额口径唯一来源：明细表聚合，绝不在 project 上冗余采购额/回款额（ADR-0004）。
- SQLite 单机下直接聚合查询，无需预聚合表。

### 2.5 明细子模块（purchase / acceptance）

标准 CRUD 深模块：`list(project_id) / create / update / delete`，内含"project_id 必须存在"校验与金额非负校验（采购额、回款额允许为 0）。

## 3. 数据模型

```sql
projects(id, name, customer, contract_no,
         initial_stage, current_stage,        -- 9 阶段枚举
         contract_amount, owner, start_date, end_date, note,
         created_at, updated_at)

nodes(id, project_id FK, parent_id FK->nodes.id NULL,  -- 锚点 parent 为空
      name, stage_key NULL,               -- 仅 9 锚点有值(商机…结算)
      sort_order, created_at, updated_at)
      -- 冗余 project_id：整树单条件可取；service 保证子节点与 parent 同项目

attachments(id, node_id FK, original_name, stored_path,
            size, mime, uploaded_at)

purchase_orders(id, project_id FK, name, supplier,
                amount, order_date, note, created_at)

acceptance_records(id, project_id FK, name, acceptance_date,
                   received_amount, note, created_at)

stage_history(id, project_id FK, from_stage, to_stage, changed_at)
```

不变量（service 层保证）：nodes 树无环且同项目；锚点恰 9 个且不可删；采购额=Σ、回款额=Σ（只算不存）。

## 4. API 设计（薄适配层）

```
POST   /api/projects                     新建（含 initial_stage）
GET    /api/projects?keyword=&stage=     列表/检索
GET    /api/projects/{id}/ledger         一账详情（聚合）
PUT    /api/projects/{id}                编辑
PATCH  /api/projects/{id}/stage          阶段流转
POST   /api/nodes                        加子环节 {parent_id, name}
PATCH  /api/nodes/{id}                   改名/排序
DELETE /api/nodes/{id}                   删子环节（非空报 409）
POST   /api/nodes/{id}/attachments       附件上传（multipart）
GET    /api/nodes/{id}/attachments       节点附件列表
GET    /api/attachments/{id}/download    下载
DELETE /api/attachments/{id}             删除
GET    /api/projects/{id}/purchases      采购 CRUD（GET列表/POST）
PUT/DELETE /api/purchases/{id}
GET    /api/projects/{id}/acceptances    验收 CRUD（对称）
PUT/DELETE /api/acceptances/{id}
GET    /api/stats                        三口径卡片
GET    /api/stats/export                 导出 xlsx（流式返回）
```

统一错误契约：`{code, message}`，404=不存在，409=状态冲突（删非空节点），422=参数校验。

## 5. 前端结构

```
frontend/src/
├── api/          # axios 实例 + 按资源封装（projects/nodes/attachments/stats）
├── views/
│   ├── ProjectList.vue    # 检索框 + 表格 + 新建对话框
│   ├── ProjectDetail.vue  # 一账制页面
│   └── StatsView.vue      # 三卡片 + 导出按钮
└── components/
    ├── StageStepper.vue   # 顶部阶段条（el-steps，点击流转）
    ├── NodeTreePanel.vue  # el-tree 环节树 + 附件管理抽屉
    └── AmountTables.vue   # 采购/验收两张明细表（复用对话框）
```

详情页布局（电信蓝商务风、精简单表）：
```
┌ 项目概要条（名称/客户/合同号/负责人/签约额） ┐
├ StageStepper：商机→…→结算（当前高亮，可点）    ┤
├──────────────┬────────────────┤
│ NodeTreePanel│ 采购明细表      │
│ (阶段锚点起) ├────────────────┤
│  附件挂任意层│ 验收记录表      │
└──────────────┴────────────────┘
```

## 6. 错误处理与边界

- 附件：上传失败（磁盘/大小异常）→ 500 + 不留孤儿记录（先存文件成功再写库）；删除 → 先删库记录再删文件，物理缺失容忍。
- 文件名安全：original_name 保留原名仅供展示，物理名一律 uuid。
- 阶段流转：target 非法 422；写 history 失败则整体回滚。
- 树并发：单人工具场景不做行锁，依赖 SQLite 写串行即可（写入低频）。

## 7. 测试策略

- **单元（service 接口为主）**：阶段流转全 9 态矩阵、树增删改与"非空禁止删除"、附件存删、三口径聚合正确性（含空明细=0）。
- **集成（FastAPI TestClient）**：建项目→锚点自动生成→挂子环节→传附件→加采购/验收→统计变化→导出可打开。全链路一账流程一条测试走完。
- **前端**：Vite dev 手工目检（个人工具体量，不铺 e2e）。

## 8. 目录总览

```
Project_Register/
├── backend/
│   ├── app/{main,core/{config,database},models,schemas,api,services}
│   └── tests/{test_project_service,test_tree_service,test_storage,test_stats,api_smoke}
├── frontend/
│   └── src/{api,views,components}
├── data/            # ledger.db + uploads/（.gitignore）
├── docs/            # 全套过程文档
└── CONTEXT.md
```