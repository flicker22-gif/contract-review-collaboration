# 合同审查协作工具

法务上传合同（Word / PDF）后，在线高亮风险条款并写批注，业务方逐条回复，支持批注状态流转（待处理 / 已解决）。

## 技术栈

- **前端**：Next.js 14 + TypeScript + Tailwind CSS（`frontend/`）
- **后端**：Python 3.11 + FastAPI + SQLite（`backend/`）
- **文档解析**：python-docx（.docx）、PyMuPDF（.pdf），统一解析为段落文本，高亮按「段落 + 字符偏移」锚定

## 启动

### 后端（端口 8001）

```bash
cd backend
python3 -m venv --without-pip .venv   # 首次
.venv/bin/python /tmp/get-pip.py      # 首次（本机 python 无自带 pip 时）
.venv/bin/pip install -r requirements.txt  # 首次
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

- API 文档：http://localhost:8001/docs
- 数据库文件：`backend/app.db`（首次启动自动建表）
- 上传的原始文件：`backend/storage/`

### 前端（端口 3200）

```bash
cd frontend
npm install   # 首次
npm run dev -- --port 3200
```

打开 http://localhost:3200

> 前端默认请求 `http://localhost:8001`，可用环境变量 `NEXT_PUBLIC_API_URL` 覆盖。

## 使用流程

> **本环境提示**：该环境会定期向后台进程发 SIGTERM 回收它们（Node 进程能幸存，Python 进程会被杀）。后端已用看门狗脚本（`/tmp/backend-watchdog.sh`，退出后 2 秒自动重启）方式启动。若发现后端无响应，重新执行：`setsid nohup /tmp/backend-watchdog.sh >/dev/null 2>&1 &`

1. 首页拖拽或选择 .docx / .pdf 合同上传，后端自动解析为段落文本
2. 进入审查页，在右上角填写姓名并选择角色（法务 / 业务），localStorage 会记住
3. 在左侧文档中**划选文字** → 弹出批注框 → 写下风险点/修改建议
4. 右侧批注面板逐条回复讨论，可按「全部 / 待处理 / 已解决」筛选
5. 点击批注卡片 ↔ 点击高亮，两侧互相滚动定位
6. 讨论完毕后点「标记已解决」

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/documents/` | 上传合同（multipart），自动解析段落 |
| GET | `/api/documents/` | 合同列表（含批注统计） |
| GET | `/api/documents/{id}` | 合同详情 + 段落 |
| GET | `/api/documents/{id}/annotations` | 批注列表（嵌套回复） |
| POST | `/api/documents/{id}/annotations` | 创建批注（段落偏移锚定） |
| PATCH | `/api/annotations/{id}` | 切换待处理/已解决 |
| DELETE | `/api/annotations/{id}` | 删除批注 |
| POST | `/api/annotations/{id}/replies` | 添加回复 |

## 后续规划

- 生成带修改建议的审查报告（导出 Word/PDF）
- 用户登录与权限（法务/业务角色固化）
- 保留原版式的文档渲染
