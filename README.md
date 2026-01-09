# AI Insight Tracker

> 🔬 基于 Multi-Agent 的智能学术与资讯追踪系统

AI Insight Tracker 是一个自动化的学术论文和 AI 技术热点追踪系统，结合 LLM 浅度分析和 Multi-Agent 深度研究能力，每日推送智能摘要到飞书。

## ✨ 核心功能

| 功能 | 描述 |
|------|------|
| 📚 **论文追踪** | 通过 arXiv API 自动获取指定分类的最新论文 |
| 🔥 **AI 新闻** | 从 AI 头部公司博客获取第一手资讯（OpenAI、Anthropic、DeepSeek、Google Research、DeepMind、Qwen 等） |
| 🤖 **浅度分析** | LLM 自动生成结构化论文/新闻摘要 |
| 🔬 **深度分析** | Multi-Agent 系统对指定论文深入研究，支持论文全文分析 |
| 📄 **全文分析** | 自动下载 PDF、解析章节结构、提取表格和图表，基于全文内容进行深度分析 |
| 📊 **每日报告** | 生成学术日报，推送到飞书 |
| 🌐 **Web 展示** | GitHub Pages 静态站浏览 |

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI Insight Tracker                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  触发层     定时触发 (GitHub Actions)  │  Issue 触发 (深度分析) │
│                      │                           │               │
│  采集层     arXiv API  │  新闻获取 (RSS + Crawler)              │
│                      │                                           │
│  分析层     浅度分析 (LangChain)  │  深度分析 (LangGraph)        │
│                      │                                           │
│  输出层     飞书通知  │  数据存储  │  GitHub Pages              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 本地开发

#### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/ai-insight-tracker.git
cd ai-insight-tracker
```

#### 2. 运行初始化脚本

```bash
./setup.sh
```

脚本会自动：
- 创建 Conda 环境 (`ai-insight-tracker`)
- 安装所有依赖
- 创建配置文件
- 交互式配置 LLM 提供商

#### 3. 激活环境

```bash
conda activate ai-insight-tracker
```

#### 4. 验证配置

```bash
python scripts/validate_config.py
```

#### 5. 手动执行任务

```bash
# 执行全部任务
python scripts/daily_crawl.py --task all

# 或分步执行
python scripts/daily_crawl.py --task arxiv     # arXiv 论文获取
python scripts/daily_crawl.py --task news      # 新闻获取
python scripts/daily_crawl.py --task analyze   # 浅度分析
python scripts/daily_crawl.py --task summary   # 生成日报
python scripts/daily_crawl.py --task notify    # 发送通知
```

### GitHub Actions 部署

#### 1. Fork 本仓库

#### 2. 配置 Secrets

在仓库 **Settings → Secrets and variables → Actions** 中添加：

| Secret | 说明 | 必需 |
|--------|------|------|
| `LLM_API_KEY` | LLM API Key（对应 LLM_PROVIDER） | ✅ |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook URL | ⚠️ 通知功能需要 |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | ⚠️ 深度分析需要 |

#### 3. 配置 Variables

| Variable | 说明 | 默认值 |
|----------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | `deepseek` |
| `LLM_MODEL` | LLM 模型 | `deepseek-chat` |
| `CATEGORIES` | arXiv 分类 | `cs.AI,cs.CL,cs.CV,cs.LG` |
| `LANGUAGE` | 输出语言 | `zh` |
| `ARXIV_MAX_RESULTS` | arXiv 每页最大返回数（分页时为 page size） | `100` |
| `ARXIV_MAX_PAGES` | arXiv 每分类最多分页次数（安全上限） | `20` |

#### 4. 启用 GitHub Pages

**Settings → Pages → Source → GitHub Actions**

#### 5. 等待每日自动运行

工作流每天 UTC 01:30（北京时间 09:30）自动执行，也可手动触发。

## ⚙️ 配置说明

### 配置优先级

```
config/settings.yaml (最高) > 环境变量 > 默认值 (最低)
```

### 配置文件

| 文件 | 用途 | 是否提交 |
|------|------|----------|
| `config/settings.yaml` | 用户配置（含 API Key） | ❌ 被 .gitignore 忽略 |
| `config/settings.example.yaml` | 配置模板 | ✅ 提交到仓库 |
| `config/news_sources.yaml` | AI 公司新闻源配置 | ✅ 提交到仓库 |

### 支持的 LLM 提供商

| 提供商 | LLM_PROVIDER 值 | API Base URL |
|--------|-----------------|--------------|
| DeepSeek | `deepseek` | `https://api.deepseek.com/v1` |
| OpenAI | `openai` | `https://api.openai.com/v1` |
| Anthropic | `anthropic` | `https://api.anthropic.com/v1` |
| Qwen | `qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Gemini | `gemini` | `https://generativelanguage.googleapis.com/v1beta/openai` |
| 智谱 | `zhipu` | `https://open.bigmodel.cn/api/paas/v4` |
| OpenRouter | `openrouter` | `https://openrouter.ai/api/v1` |
| Grok | `grok` | `https://api.x.ai/v1` |

> **注意**: 统一使用 `LLM_API_KEY` 环境变量配置 API Key，需与 `LLM_PROVIDER` 对应。

### 新闻源

项目支持从以下 AI 公司获取新闻：

| 公司 | 获取方式 | 状态 |
|------|----------|------|
| OpenAI | RSS | ✅ |
| Microsoft Research | RSS | ✅ |
| Amazon AWS ML | RSS | ✅ |
| Anthropic | Crawler | ✅ |
| DeepSeek | Crawler | ✅ |
| Google Research | Crawler | ✅ |
| DeepMind | Crawler | ✅ |
| Gemini | Crawler | ✅ |
| Qwen (通义千问) | Crawler | ✅ |

## 📁 项目结构

```
ai-insight-tracker/
├── src/                          # 核心源代码
│   ├── config/                   # 配置系统
│   │   ├── models.py             # 配置数据模型
│   │   ├── loader.py             # 配置加载器
│   │   └── check.py              # 首次运行检测
│   ├── models/                   # Pydantic 数据模型
│   │   ├── common.py             # 共享类型定义 (Tags, Keywords)
│   │   ├── paper.py              # 论文模型 (Paper, PaperLightAnalysis, AnalyzedPaper)
│   │   ├── news.py               # 热点模型 (NewsItem, NewsLightAnalysis, AnalyzedNews)
│   │   └── daily_report.py       # 日报模型
│   ├── llm/                      # LLM 客户端
│   │   ├── client.py             # 统一客户端接口
│   │   ├── providers.py          # 提供商配置
│   │   ├── exceptions.py         # 异常定义
│   │   └── deepseek_reasoner.py  # DeepSeek Reasoner 工具调用适配器
│   ├── data_fetchers/            # 数据采集模块
│   │   ├── arxiv/                # arXiv API 客户端
│   │   │   ├── client.py         # 异步客户端
│   │   │   ├── query.py          # 查询构建器
│   │   │   └── dedup.py          # 去重逻辑（已废弃）
│   │   ├── processed_tracker.py  # 已处理内容追踪器（统一去重，7天自动清理）
│   │   ├── pdf/                  # PDF 处理模块 (论文全文分析)
│   │   │   ├── downloader.py     # PDF 异步下载器
│   │   │   ├── parser.py         # PDF 解析器 (PyMuPDF + pdfplumber)
│   │   │   ├── chunker.py        # 智能分块器
│   │   │   └── models.py         # 数据模型
│   │   ├── news/                 # 新闻源统一入口
│   │   │   ├── fetcher.py        # 混合获取器 (RSS + Crawler)
│   │   │   ├── rss_fetcher.py    # RSS 异步获取器
│   │   │   ├── rss_parser.py     # RSS 解析器
│   │   │   └── sources.py        # 新闻源配置加载
│   │   └── crawler/              # Web 爬虫模块 (crawl4ai)
│   │       ├── client.py         # 异步爬虫客户端
│   │       ├── base.py           # 提取器基类
│   │       └── extractors/       # 各网站专用提取器
│   │           ├── anthropic.py
│   │           ├── deepseek.py
│   │           ├── deepmind.py
│   │           ├── gemini.py
│   │           ├── google_research.py
│   │           └── qwen.py
│   ├── prompts/                  # 统一 Prompt 模板目录
│   │   ├── prompt_loader.py      # 统一 Prompt 加载器
│   │   ├── paper.py              # 论文分析 Prompt
│   │   ├── news.py               # 热点分析 Prompt
│   │   └── report.py             # 日报生成 Prompt
│   ├── agents/                   # 分析模块
│   │   ├── shared.py             # 全局共享资源 (LLM Semaphore)
│   │   ├── base_analyzer.py      # 浅度分析器泛型基类
│   │   ├── paper/                # 论文分析
│   │   │   ├── light_analyzer.py # 浅度分析器
│   │   │   └── deep_analyzer/    # 深度分析 (LangGraph Multi-Agent)
│   │   │       ├── state.py      # 状态定义
│   │   │       ├── graph.py      # 工作流图
│   │   │       ├── nodes/        # Agent 节点 (supervisor, researcher, writer, reviewer)
│   │   │       └── tools/        # 工具
│   │   │           ├── search.py         # 网络搜索工具 (Tavily/DuckDuckGo)
│   │   │           ├── arxiv_loader.py   # arXiv 论文加载器
│   │   │           ├── paper_reader.py   # 论文全文查询工具
│   │   │           └── react_executor.py # ReAct Agent 执行器
│   │   └── news/                 # 热点分析
│   │       └── light_analyzer.py # 浅度分析器
│   ├── generators/               # 内容生成
│   │   └── daily.py              # 日报生成器
│   ├── notifiers/                # 通知模块
│   │   ├── base.py               # 通知器基类
│   │   ├── feishu.py             # 飞书异步通知器
│   │   └── templates/            # 卡片模板
│   └── utils/                    # 工具函数
├── scripts/                      # 执行脚本
│   ├── daily_crawl.py            # 每日任务入口
│   ├── deep_analysis.py          # 深度分析入口
│   ├── notify.py                 # 通知脚本
│   ├── validate_config.py        # 配置验证
│   └── update_config.py          # 配置更新工具
├── config/                       # 配置文件
│   ├── settings.example.yaml     # 配置模板
│   └── news_sources.yaml         # AI 公司新闻源配置
├── data/                         # 数据存储
│   ├── papers/                   # 论文数据 (JSON)
│   ├── news/                     # 热点数据 (JSON)
│   ├── reports/                  # 日报数据 (JSON)
│   └── analysis/deep/            # 深度分析结果 (Markdown)
├── app/frontend/                 # React 前端
│   ├── src/
│   │   ├── components/           # UI 组件
│   │   │   ├── business/         # 业务组件 (PaperCard, NewsCard 等)
│   │   │   ├── layout/           # 布局组件
│   │   │   └── ui/               # 通用 UI 组件
│   │   ├── pages/                # 页面组件
│   │   ├── hooks/queries/        # 数据查询 Hooks
│   │   ├── lib/                  # 工具库
│   │   └── types/                # TypeScript 类型定义
│   └── dist/                     # 构建输出
├── tests/                        # 测试套件
│   ├── unit/                     # 单元测试
│   ├── fixtures/                 # 测试数据
│   └── conftest.py               # Pytest 配置
├── .github/workflows/            # GitHub Actions 工作流
│   ├── daily.yml                 # 每日定时工作流
│   └── deep_analysis.yml         # Issue 触发深度分析
├── setup.sh                      # 项目初始化脚本
├── environment.yml               # Conda 环境配置
├── requirements.txt              # Python 依赖
└── requirements-dev.txt          # 开发依赖
```

## 🔧 技术栈

### 后端

| 类别 | 技术 |
|------|------|
| 运行时 | Python 3.12+ |
| 架构 | 全异步设计 (asyncio + aiohttp) |
| 数据采集 | arXiv 官方 API、crawl4ai + Playwright |
| PDF 处理 | PyMuPDF (文本提取) + pdfplumber (表格提取) |
| LLM 调用 | LangChain 统一接口 (`init_chat_model`) |
| Multi-Agent | LangGraph 工作流 |
| 数据验证 | Pydantic v2 |
| 进度显示 | tqdm (异步进度条) |

### LLM 集成

- **langchain-openai**: OpenAI / DeepSeek / Qwen / 智谱 / Grok / OpenRouter
- **langchain-anthropic**: Anthropic Claude
- **langchain-google-genai**: Google Gemini
- **结构化输出**: `with_structured_output()` 自动选择最佳策略
  - 优先级: `json_schema` > `function_calling` > `json_mode`
  - 自动检测模型能力，如 `deepseek-reasoner` 自动回退到 `json_mode`

### 前端

| 类别 | 技术 |
|------|------|
| 框架 | React 18 + TypeScript |
| 构建 | Vite |
| 样式 | TailwindCSS |
| 状态管理 | Zustand |

### 基础设施

| 类别 | 技术 |
|------|------|
| CI/CD | GitHub Actions |
| 静态托管 | GitHub Pages |
| 通知 | 飞书 Webhook (异步) |

## 🎯 深度分析触发

在飞书日报卡片中点击「请求深度分析」按钮，会跳转到 GitHub 创建 Issue。

Issue 必须满足：
- 标签包含 `agent-task`
- 标题以 `[Analysis]` 开头
- 创建者为仓库 Owner

## 💰 成本估算

| 项目 | 日均成本 (CNY) |
|------|---------------|
| 浅度分析 (50篇) | 0.3-0.5 |
| 深度分析 (每次) | 0.5-2.0 |
| GitHub Actions | 免费 |
| GitHub Pages | 免费 |

## 🧪 测试

项目包含完整的单元测试套件：

```bash
# 安装测试依赖
pip install -r requirements-dev.txt

# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/unit/models/ -v
pytest tests/unit/llm/ -v
pytest tests/unit/agents/ -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```
