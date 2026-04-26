# 飞书文档 Skill

Claude Code 飞书云文档读写技能

## 功能

- 读取/创建/编辑飞书云文档
- 搜索文档
- 操作多维表格（Bitable）
- 操作白板（Whiteboard）
- 操作知识库（Wiki）

## 目录结构

```
~/.claude/skills/feishu-doc/
├── SKILL.md              # 技能定义
├── scripts/
│   ├── feishu.py         # CLI 入口
│   ├── auth.py           # 授权配置
│   ├── crypto.py         # AES-256-GCM 加解密
│   ├── feishu_client.py  # MCP 客户端
│   └── url_parser.py     # URL 解析
└── README.md
```

```
~/.feishu-claude/          # 密钥目录
├── key.bin                # 加密密钥
└── secrets.json           # 加密凭证
```

## 安装步骤

### 1. 安装依赖

```bash
pip install cryptography
```

### 2. 配置应用凭证

CMD中交互式配置：

```bash
cd ~/.claude/skills/feishu-doc/scripts
python auth.py setup
```

按提示输入：
- App ID（飞书应用 ID）
- App Secret（飞书应用密钥）
- 在浏览器中完成飞书授权


### 3. 验证配置

```bash
python auth.py status
```

## 使用方法

在 Claude Code 中直接使用自然语言：

```
# 读取文档
分析这个飞书文档 https://xxx.feishu.cn/docx/ABC123

# 创建文档
创建一个飞书文档，标题叫"项目计划"

# 追加内容
在文档 ABC123 末尾添加"总结：本文已完成"

# 搜索文档
搜索飞书中关于"技术方案"的文档

# 查看评论
获取文档 ABC123 的评论
```

## 命令行使用

```bash
cd ~/.claude/skills/feishu-doc/scripts

# 读取文档
python orchestrator.py read "https://xxx.feishu.cn/docx/ABC123"

# 创建文档
python orchestrator.py create "文档标题"

# 搜索
python orchestrator.py search "关键词"

# 列出
python orchestrator.py list
```

## 安全说明

- 密钥存储在 `~/.feishu-claude/key.bin`
- 凭证加密存储在 `~/.feishu-claude/secrets.json`
- 敏感文件不提交到版本控制（已配置 .gitignore）
- 密钥和凭证仅本地存储，不上传到任何服务器

## 密钥轮换

如需轮换密钥：

```bash
python -c "from crypto import rotate_key; rotate_key()"
```

这将生成新密钥并重新加密所有凭证。

## 故障排除

### 密钥不存在

```bash
python auth.py setup
```

### Token 过期

```bash
python auth.py refresh
```

### 查看状态

```bash
python auth.py status
```

## 权限要求

在飞书开放平台申请以下权限：

- `docx:document` - 文档权限
- `docx:document:readonly` - 查看文档
- `docx:document:block:convert` - 块转换
- `drive:drive` - 云空间
- `wiki:wiki` - 知识库
- `board:whiteboard:node:*` - 白板
- `bitable:app:*` - 多维表格