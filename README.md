# 个人记账 + 家庭台账

两个纯前端网页应用，数据存 localStorage，可离线使用。

## 应用列表

| 应用 | 文件 | 部署地址 |
|------|------|----------|
| 家庭台账 | `index.html` | `https://gcore.jsdelivr.net/gh/JiaLing12138/jizhang@main/`（国内直连） |
| 个人记账本 | `personal.html` | `https://gcore.jsdelivr.net/gh/JiaLing12138/jizhang@main/personal.html`（国内直连） |

## 功能

### 家庭台账
- 借出款管理（借款人、金额、利率、约定归还日）
- 存款记录（含利息预估）
- 大块资产（房产/车产等）
- 家庭净值总览

### 个人记账本
- 日常收支流水（按月分组）
- 18 个支出分类 + 6 个收入分类 + 5 个资产分类
- 存款计划（目标 + 进度条 + 存入记录）
- 月度总览（支出/收入/结余/存入）
- **iOS 快捷指令 OCR 预填**：截屏 → 本地规则识别金额/分类/备注/日期/退款（默认快速通道，无需 App）
- **豆包 AI 识别（可选）**：豆包版捷径仍可用，但日常默认走本地规则（快）
- **备份 + 导入恢复**：一键导出 JSON 备份，可随时覆盖恢复（防网址过期/换设备丢数据）
- **防误存**：金额统一校验（>0 且 <1000 万，保留两位小数）；同一天同分类同金额自动提示可能重复
- **隐私**：页面打开后立即清空地址栏的 OCR/豆包参数，避免账单内容被统计脚本上报或刷新重跑

## 本地开发

### 启动本地服务器

```bash
cd /Users/liujialin/记账
python3 -m http.server 8000 --bind 127.0.0.1
```

服务器启动后：
- 本机访问：`http://127.0.0.1:8000/`（勿用 192.168.x 地址，会被 VPN 劫持）

注：服务必须用常驻后台方式启动，否则对话轮次结束会被回收。

获取 Mac IP：
```bash
ipconfig getifaddr en0
```

### 修改流程

1. 编辑 `personal.html` 或 `index.html`
2. 用 `bash scripts/start-server.sh` 起本地服务，浏览器打开 `http://127.0.0.1:8000/personal.html` 预览
3. 确认无误后重新部署到云端（见部署章节）

## 部署

使用 GitHub Pages 部署（免费、网址永久稳定）：
- 本目录本身就是 git 仓库，远程为 `JiaLing12138/jizhang`（Public）；`.workbuddy/` 已用 .gitignore 排除，不会上传
- **更新**：改完文件后运行 `bash scripts/publish.sh`（提交 → 推送 → 刷 CDN 缓存，约 1 分钟生效，网址不变）
- **国内直连地址（日常使用）**：`https://gcore.jsdelivr.net/gh/JiaLing12138/jizhang@main/personal.html`

## URL 参数（个人记账本快捷指令）

| 参数 | 说明 | 示例 |
|------|------|------|
| `?ocr=<URL编码文本>` | OCR 文字，自动解析金额+分类 | `?ocr=微信支付38.50元` |
| `?text=<URL编码文本>` | 同 ocr | |
| `?amt=&cat=&note=&date=` | 直接传结构化参数 | `?amt=38.5&cat=餐饮` |
| `?ai=<URL编码JSON>` | 豆包识别结果（金额/分类/备注），优先于本地规则 | `?ai={"amt":"6","cat":"购物"}` |
| `?ai 的 date 字段` | 豆包返回交易日期（YYYY-MM-DD）时自动填入日期框 | |
| `?quick=1` | 网页弹窗问金额+分类 | |
| `&auto=1` | 零点击自动保存 | `?ocr=...&auto=1` |

## 文件结构

```
记账/
├── personal.html       # 个人记账本（源文件，直接编辑）
├── index.html          # 家庭台账（源文件，直接编辑）
├── scripts/            # 工具：publish.sh 发布 / gen_shortcut.py 生成 / test_ocr.js 测试 / start-server.sh 预览
├── shortcuts/          # 生成的快捷指令（AirDrop 从这里拿）
├── .git/               # git 仓库（远程 = GitHub）
├── .gitignore          # 排除 .workbuddy/ 等内部文件
└── README.md
```

## 快捷指令安装

1. 从 `shortcuts/` 用 AirDrop 发到 iPhone
2. 常用：`记账OCR.shortcut`（本地规则，快）；`记账OCR豆包.shortcut` 为可选 AI 版
3. 页面地址：`https://gcore.jsdelivr.net/gh/JiaLing12138/jizhang@main/personal.html`
