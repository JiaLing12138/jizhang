# iOS 快捷指令（记账 OCR）

三个快捷指令均已完成苹果签名（`shortcuts sign --mode anyone`），iPhone 直接 AirDrop 或从"文件"App
打开即可导入（首次导入可能提示"不受信任的快捷指令"，去 设置 → 快捷指令 → 允许不受信任的快捷指令 打开即可）。

## 选哪个？

| 文件 | 定位 | 说明 |
|------|------|------|
| `记账OCR本地版.shortcut` | **日常正式版**（推荐） | 截屏 → 本地规则识别 → 复制到剪贴板 → 打开 Scriptable 记账页预填确认。完全离线，不依赖任何网址 |
| `记账OCR.shortcut` | 网页版备用 | 纯本地规则识别，跳转网页（需网页可访问） |
| `记账OCR豆包.shortcut` | 网页版备用 | 豆包 AI 识别（需安装豆包 App + 网页可访问） |
| `记账OCR豆包-调试.shortcut` | 诊断用 | 豆包版 + 弹窗显示原始输出 |

## 怎么用

1. **本地版**：先在 iPhone 装好 Scriptable，打开一次确认 iCloud 同步出 `记账` 脚本（文件 App → iCloud 云盘 → Scriptable）
2. 导入 `记账OCR本地版.shortcut`（删掉旧的同名捷径再导入新的）
3. 在微信/支付宝账单页 **背面双击**（或手动运行捷径）触发
4. Scriptable 自动打开记账页并预填金额/分类/备注/日期 → 核对后点保存（首次会询问是否允许读取剪贴板，允许即可）

## 工作方式

- 截屏 → 裁掉顶部状态栏 → 提取文字 → 复制到剪贴板 → 打开 `scriptable:///run/记账?clip=1`
- Scriptable 读剪贴板 → 本地规则识别金额/分类/备注/日期/退款 → 预填表单待确认
- 数据写入 `iCloud 云盘/Scriptable/记账数据.json`

> 本地版快捷指令由 `scripts/gen_shortcut_local.py` 生成（改后重跑并重签），
> 生成后的文件同步提交到本目录。网页版快捷指令由 `scripts/gen_shortcut.py` 生成。
