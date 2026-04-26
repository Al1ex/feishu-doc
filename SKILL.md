---
name: feishu-doc
description: |
  飞书文档读写技能 - 读取、创建、编辑飞书云文档，支持文档、Wiki、多维表格、白板等类型。
  当用户提及飞书文档链接或请求操作飞书文档时激活。
---

# 飞书文档 Skill

用于在 Claude Code 中操作飞书云文档的技能。

## 触发条件

- 用户提及飞书文档链接（`https://xxx.feishu.cn/docx/xxx` 或 `/wiki/xxx`）
- 用户请求创建、读取、编辑飞书文档
- 用户请求操作多维表格或白板

## 支持的操作

### 文档操作
- **fetch-doc**: 读取文档内容
- **create-doc**: 创建新文档
- **update-doc**: 更新/追加文档内容
- **list-docs**: 列出文档
- **search-doc**: 搜索文档
- **get-comments**: 获取评论
- **add-comments**: 添加评论

### 多维表格操作
- **fetch-bitable**: 读取表格数据
- **create-bitable**: 创建表格
- **update-bitable**: 更新表格

### 白板操作
- **fetch-whiteboard**: 读取白板
- **create-whiteboard**: 创建白板
- **update-whiteboard**: 更新白板

### Wiki 操作
- **list-wiki**: 列出知识库
- **get-wiki-node**: 获取知识库节点

## 使用方式

```
# 读取文档
分析这个飞书文档 https://xxx.feishu.cn/docx/ABC123def

# 创建文档
帮我创建一个飞书文档，标题叫"技术方案"

# 追加内容
在文档 ABC123 末尾添加"总结：本文档已完成"

# 搜索文档
搜索飞书中关于"项目计划"的文档
```

## 首次配置

```bash
cd ~/.claude/skills/feishu-doc/scripts
python feishu.py setup
```

## 命令行使用

```bash
python feishu.py help              # 显示帮助
python feishu.py status            # 配置状态
python feishu.py create "标题"     # 创建文档
python feishu.py read "url"       # 读取文档
python feishu.py search "关键词"   # 搜索
python feishu.py list            # 列出文档
```