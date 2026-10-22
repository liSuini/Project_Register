# 交接文档（Handoff）· 项目台账系统

> 日期：2026-10-22 ｜ 交付状态：**MVP+完整版全部完成**，29 项后端测试全绿，三页面浏览器实测通过，已推送 GitHub

## 一、这是什么

本机运行的"一个项目一本账"台账系统：9 阶段锚点树归档 + 自由阶段流转 + 采购/验收明细 + 三口径统计导出。个人工具，无登录，SQLite + 本地文件系统。

## 二、如何运行

```powershell
.\start.ps1       # 一键：前端 http://localhost:3000  后端 http://127.0.0.1:8100/docs
```

- 端口决策：后端 **8100**（本机 8000 被 BidAlert 占用），前端 3000（vite 代理 /api → 8100）
- 备份 = 拷贝 `backend/data/` 整目录（ledger.db + uploads/）

## 三、架构地图（引用，勿重复阅读全文）

| 主题 | 参照 |
|------|------|
| 术语表（9阶段/锚点/三口径定义） | `CONTEXT.md` |
| 4 条关键决策（技术栈/锚点树/附件文件系统/明细平级） | `docs/adr/0001~0004` |
| 分层与接口清单 | `docs/specs/2026-10-22-architecture-design.md` |
| 23 条用户故事与实现决策 | `docs/specs/2026-10-22-technical-spec.md` |
| 13 任务 TDD 全码（含每个文件职责） | `docs/plans/2026-10-22-project-ledger-plan.md` |
| 逻辑原型（可双击体验） | 分支 `prototype/ledger-logic-v1`；本地 `.temp/prototype/ledger-logic-prototype.html` |

代码结构：`backend/app/{core,models,schemas,services,api}` 深模块分层（api 薄、services 深）；`frontend/src/{api,views,components}`。

## 四、验证状态

- 后端：`cd backend; python -X utf8 -m pytest tests -v` → **29 passed**（含全链路集成：建项目→锚点→子环节→附件→明细→检索→统计→导出）
- 前端：列表页（新建/检索/筛选/跳转）、详情页（流转/确认弹窗/三层嵌套/附件上传下载删除/非空删除 409 提示/合计实时）、统计页（860/200/300 万卡片 + xlsx 导出）均已在浏览器实测
- start.ps1：幂等验证通过（重复执行跳过启动）

## 五、已知限制与后续迭代建议（按价值排序）

1. **Excel 存量导入**（PRD Non-Goal 预留）：从既有台账批量导入项目，需建临时映射模板
2. **统计图表**（ECharts 已是用户熟栈）：月度签约/回款趋势、阶段分布
3. **项目编辑入口**：当前详情页只读概要， PUT /api/projects/{id} 后端已就绪，补一个前端编辑对话框即可
4. **流转史查看**：stage_history 表已留痕，API 未暴露，补 `GET /api/projects/{id}/stage-history`
5. **采购/验收编辑**：后端 PUT 已就绪，前端仅新增+删除，补编辑同样简单
6. SQLite 并发：3-5 人内没问题；更多需换 PostgreSQL（用户有 172.16.11.7:25432）
7. 附件无类型/大小限制（办公文件实测正常，超大文件未测）

## 六、给下一个会话的建议技能

- 改后端功能 → **tdd**（测试基线已立，改动请保持 29 测试绿）
- 调整或新增页面 → **frontend-design-zh**（保持电信蓝商务风、精简单表风格）
- 继续走完整开发流程 → **fullstack-dev-master**
- 数据库迁移如上线 PostgreSQL → **supabase-postgres-best-practices**

## 七、环境备忘

- Python：`D:\developTools\python\python3.14.5\python.exe`（系统 PATH 的 python 是 TeleAgent runtime 3.12）
- 8000 端口长期被本机 BidAlert 占用，本项目一律用 8100
- push 走 SSH（liSuini@github.com，ED25519）
