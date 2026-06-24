# PK-Sim RAG Q&A

Local retrieval-augmented question answering for the Open Systems Pharmacology Suite, especially PK-Sim and MoBi documentation and forum discussions.

[中文说明](#中文说明) | [English Guide](#english-guide)

## 中文说明

### 项目简介

这是一个本地运行的 OSP Suite / PK-Sim 问答工具。它会把 PDF 手册和 Open-Systems-Pharmacology Forum Discussions 转换成本地知识库，使用 Chroma 做向量检索，再调用 DeepSeek 的 OpenAI-compatible Chat Completions API 生成中文或英文答案。

适合这些场景：

- 查询 PK-Sim、MoBi、OSP Suite 手册内容。
- 搜索 GitHub Forum 中已有的问题、回答和讨论。
- 在本机保留知识库、索引和 API 密钥。
- 每周同步新的 GitHub Discussions，持续更新本地问答库。

### API 密钥安全

本仓库不提交真实 API 密钥。

- 真实密钥只放在本地 `.env` 文件中。
- `.env`、`.env.*` 和 Streamlit secrets 已在 `.gitignore` 中忽略。
- `osp-rag-demo/.env.example` 只保留空值模板，不包含任何可用 token。
- GitHub token 只需要读取公开仓库 Discussions 的权限。
- 如果密钥曾经被提交到远端，请立即在对应平台撤销并重新生成。

推荐配置方式：

```bash
cd osp-rag-demo
cp .env.example .env
```

然后在 `.env` 中填写：

```bash
DEEPSEEK_API_KEY=
GITHUB_TOKEN=
```

### 项目结构

```text
.
├── README.md
├── .gitignore
└── osp-rag-demo/
    ├── app.py
    ├── config.py
    ├── .env.example
    ├── requirements.txt
    ├── setup.command
    ├── start_demo.command
    ├── update_knowledge_base.command
    ├── rag/
    ├── scripts/
    ├── data/
    └── storage/
```

### 准备条件

- Python 3.10 或更新版本。
- DeepSeek API key。
- GitHub personal access token，用来读取 `Open-Systems-Pharmacology/Forum` Discussions。
- PDF 文件：`osp-rag-demo/data/raw/Open Systems Pharmacology Suite.pdf`。

如果 Hugging Face 下载较慢，可以使用镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

Apple Silicon Mac 可以使用 MPS：

```bash
export EMBEDDING_DEVICE=mps
```

### Mac 快速使用

进入应用目录：

```bash
cd osp-rag-demo
```

复制配置模板并填写本地密钥：

```bash
cp .env.example .env
```

安装依赖：

```bash
./setup.command
```

初始化或更新知识库：

```bash
./update_knowledge_base.command
```

启动网页：

```bash
./start_demo.command
```

打开：

```text
http://localhost:8501
```

### 终端使用

```bash
cd osp-rag-demo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env` 后，依次运行：

```bash
python scripts/ingest_pdf.py
python scripts/ingest_github_discussions.py --all
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/build_index.py --reset
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps streamlit run app.py --server.port 8501
```

如果不是 Apple Silicon Mac，可以去掉 `EMBEDDING_DEVICE=mps`。

### 每周更新

默认只同步本地已有数据之后更新过的 GitHub Discussions：

```bash
cd osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py
```

全量重新同步 GitHub Discussions：

```bash
cd osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py --full-github
```

### 检索测试

```bash
cd osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com python scripts/test_retrieval.py "How do I install Open Systems Pharmacology Suite?" --min-score 0.70
```

中文示例：

```bash
cd osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com python scripts/test_retrieval.py "Parameter Identification 有哪三种 optimization algorithms？它们有什么区别？" --min-score 0.55
```

### 常用配置

主要配置写在 `.env`：

```bash
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

GITHUB_TOKEN=
GITHUB_OWNER=Open-Systems-Pharmacology
GITHUB_REPO=Forum

PDF_PATH=data/raw/Open Systems Pharmacology Suite.pdf
PDF_PAGES_PATH=data/processed/pdf_pages.jsonl
VECTOR_DB_DIR=storage/chroma
COLLECTION_NAME=osp_knowledge_base

EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=
TOP_K=8
MIN_RELEVANCE_SCORE=0.70
PDF_WINDOW_PAGES=1
PDF_WINDOW_STRIDE=1
PDF_CONTEXT_PAGES=4
MAX_CONTEXT_CHARS=18000
```

说明：

- `MIN_RELEVANCE_SCORE` 越高越保守，通常可设为 `0.65` 到 `0.75`。
- `TOP_K` 控制进入回答上下文的检索片段数量。
- `PDF_CONTEXT_PAGES` 会在命中 PDF 页附近补充上下文，缓解内容跨页问题。
- `MAX_CONTEXT_CHARS` 控制发送给模型的最大上下文长度。
- `EMBEDDING_DEVICE=mps` 适合 Apple Silicon Mac，其他机器可以留空。

### 数据位置

- PDF 原文：`osp-rag-demo/data/raw/`
- PDF 解析结果：`osp-rag-demo/data/processed/pdf_pages.jsonl`
- GitHub Discussions 本地库：`osp-rag-demo/data/processed/github_discussions.jsonl`
- 检索 chunks：`osp-rag-demo/data/processed/chunks.jsonl`
- Chroma 向量库：`osp-rag-demo/storage/chroma/`

删除 `osp-rag-demo/storage/chroma/` 后，可以重新运行 `build_index.py --reset` 生成索引。

### RAG 行为

- 只基于检索到的 PDF 和 GitHub Discussion 上下文回答。
- 找不到足够相关内容时，会提示当前知识库暂无足够相关内容。
- 答案会附带引用来源，方便回到 PDF 页码或 GitHub Discussion 核对。
- 支持中文、英文和中英混合提问。

### 故障排查

- 没有检测到 `DEEPSEEK_API_KEY`：确认 `.env` 位于仓库根目录或 `osp-rag-demo/` 目录，并且变量名拼写正确。
- `GITHUB_TOKEN is missing`：在 `.env` 中填写 GitHub token 后重新运行更新脚本。
- Hugging Face 模型下载慢：设置 `HF_ENDPOINT=https://hf-mirror.com`。
- Apple Silicon 速度慢：设置 `EMBEDDING_DEVICE=mps`。
- Streamlit 端口被占用：改用 `streamlit run app.py --server.port 8502`。

## English Guide

### Overview

This repository contains a local RAG question-answering tool for the Open Systems Pharmacology Suite, with a focus on PK-Sim and MoBi. It indexes local PDF documentation and Open-Systems-Pharmacology Forum discussions, retrieves relevant context with Chroma, and uses DeepSeek's OpenAI-compatible Chat Completions API to answer in Chinese or English.

Use it to:

- Ask questions about PK-Sim, MoBi, and OSP Suite documentation.
- Search previous GitHub Forum discussions and accepted answers.
- Keep the knowledge base, vector index, and API keys on your own machine.
- Refresh the local knowledge base with newly updated GitHub Discussions.

### API Key Safety

Real API keys are not committed to this repository.

- Store real keys only in a local `.env` file.
- `.env`, `.env.*`, and Streamlit secrets are ignored by Git.
- `osp-rag-demo/.env.example` is a blank template with no usable token.
- The GitHub token only needs permission to read public repository discussions.
- If a key was ever committed to a remote repository, revoke it and create a new one.

Create local configuration:

```bash
cd osp-rag-demo
cp .env.example .env
```

Then fill in:

```bash
DEEPSEEK_API_KEY=
GITHUB_TOKEN=
```

### Requirements

- Python 3.10 or newer.
- A DeepSeek API key.
- A GitHub personal access token for reading `Open-Systems-Pharmacology/Forum` Discussions.
- The PDF file at `osp-rag-demo/data/raw/Open Systems Pharmacology Suite.pdf`.

Optional environment variables:

```bash
export HF_ENDPOINT=https://hf-mirror.com
export EMBEDDING_DEVICE=mps
```

Use `EMBEDDING_DEVICE=mps` only on Apple Silicon Macs.

### Quick Start On Mac

```bash
cd osp-rag-demo
cp .env.example .env
./setup.command
./update_knowledge_base.command
./start_demo.command
```

Open:

```text
http://localhost:8501
```

### Terminal Workflow

```bash
cd osp-rag-demo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

After editing `.env`, build the local knowledge base:

```bash
python scripts/ingest_pdf.py
python scripts/ingest_github_discussions.py --all
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/build_index.py --reset
```

Start the Streamlit app:

```bash
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps streamlit run app.py --server.port 8501
```

Remove `EMBEDDING_DEVICE=mps` on non-Apple-Silicon machines.

### Refresh The Knowledge Base

Incremental update:

```bash
cd osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py
```

Full GitHub discussion refresh:

```bash
cd osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py --full-github
```

### Retrieval Test

```bash
cd osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com python scripts/test_retrieval.py "How do I install Open Systems Pharmacology Suite?" --min-score 0.70
```

### Main Configuration

The main settings live in `.env`:

```bash
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

GITHUB_TOKEN=
GITHUB_OWNER=Open-Systems-Pharmacology
GITHUB_REPO=Forum

PDF_PATH=data/raw/Open Systems Pharmacology Suite.pdf
PDF_PAGES_PATH=data/processed/pdf_pages.jsonl
VECTOR_DB_DIR=storage/chroma
COLLECTION_NAME=osp_knowledge_base

EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=
TOP_K=8
MIN_RELEVANCE_SCORE=0.70
PDF_WINDOW_PAGES=1
PDF_WINDOW_STRIDE=1
PDF_CONTEXT_PAGES=4
MAX_CONTEXT_CHARS=18000
```

### Data Locations

- Source PDFs: `osp-rag-demo/data/raw/`
- Parsed PDF pages: `osp-rag-demo/data/processed/pdf_pages.jsonl`
- Local GitHub Discussions: `osp-rag-demo/data/processed/github_discussions.jsonl`
- Retrieval chunks: `osp-rag-demo/data/processed/chunks.jsonl`
- Chroma vector store: `osp-rag-demo/storage/chroma/`

### RAG Behavior

- The app answers only from retrieved PDF and GitHub Discussion context.
- If the knowledge base does not contain enough relevant context, it returns an insufficient-context message.
- Answers include citations for manual verification.
- Chinese, English, and mixed-language questions are supported.

### Troubleshooting

- Missing `DEEPSEEK_API_KEY`: check that `.env` exists in the repository root or `osp-rag-demo/`.
- `GITHUB_TOKEN is missing`: add a GitHub token to `.env` and rerun the update script.
- Slow Hugging Face downloads: set `HF_ENDPOINT=https://hf-mirror.com`.
- Slow embedding on Apple Silicon: set `EMBEDDING_DEVICE=mps`.
- Port already in use: run `streamlit run app.py --server.port 8502`.
