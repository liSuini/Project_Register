# 技术栈：FastAPI + SQLite + Vue3 单仓库

个人工具（2-3 人、本机运行、无登录），选定 Python FastAPI + SQLAlchemy + SQLite 作后端，Vue3 + Vite + Element Plus 作前端，前后端同仓库（`backend/` 与 `frontend/`），单进程部署。选择理由：与既有 BidAlert 技术栈完全一致，维护心智不变；SQLite 免数据库服务，备份即拷文件；FastAPI 自带 OpenAPI 文档便于自测。曾考虑纯 HTML 单文件（交付最简但树形交互受限，放弃）。锁定期长（换库=全部重写），故记录。
