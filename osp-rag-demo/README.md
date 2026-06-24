# OSP Suite Local RAG Q&A

This folder contains the Streamlit application for the PK-Sim / OSP Suite local RAG question-answering tool.

[中文说明](#中文说明) | [English Guide](#english-guide)

## 中文说明

### 这是什么

这是一个本地运行的 Open Systems Pharmacology Suite 知识库问答工具。它会把本地 PDF 手册和 GitHub Discussions 整理成知识库，使用 Chroma 向量库检索，再调用 DeepSeek 生成中文或英文答案。

根目录的 `README.md` 是面向 GitHub 首页的完整说明；本文件保留应用目录内的快速使用说明。

### API 密钥

真实密钥只放在本地 `.env` 文件中，不要提交到 GitHub。

本仓库已经忽略：

- `.env`
- `.env.*`
- `.streamlit/secrets.toml`
- 本地虚拟环境、缓存和向量库

复制模板：

```bash
cp .env.example .env
```

然后填写：

```bash
DEEPSEEK_API_KEY=
GITHUB_TOKEN=
```

GitHub token 只需要读取公开仓库 Discussions 的权限。

### Mac 快速使用

如果你在仓库根目录：

```bash
cd osp-rag-demo
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
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env` 后运行：

```bash
python scripts/ingest_pdf.py
python scripts/ingest_github_discussions.py --all
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/build_index.py --reset
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps streamlit run app.py --server.port 8501
```

不是 Apple Silicon Mac 时，可以去掉 `EMBEDDING_DEVICE=mps`。

### 每周更新

```bash
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py
```

全量更新 GitHub Discussions：

```bash
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py --full-github
```

### 常用配置

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

### 数据位置

- PDF 原文：`data/raw/`
- PDF 解析结果：`data/processed/pdf_pages.jsonl`
- GitHub Discussions 本地库：`data/processed/github_discussions.jsonl`
- 检索 chunks：`data/processed/chunks.jsonl`
- Chroma 向量库：`storage/chroma/`

## English Guide

### What It Is

This is a local RAG question-answering tool for the Open Systems Pharmacology Suite. It indexes local PDF documentation and GitHub Discussions, retrieves context with Chroma, and uses DeepSeek to answer in Chinese or English.

The root `README.md` is the full GitHub-facing guide. This file keeps the app-folder quick start.

### API Keys

Store real keys only in a local `.env` file. Do not commit `.env` to GitHub.

The repository ignores:

- `.env`
- `.env.*`
- `.streamlit/secrets.toml`
- local virtual environments, caches, and vector stores

Create local config:

```bash
cp .env.example .env
```

Then fill in:

```bash
DEEPSEEK_API_KEY=
GITHUB_TOKEN=
```

The GitHub token only needs permission to read public repository discussions.

### Quick Start On Mac

From the repository root:

```bash
cd osp-rag-demo
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
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

After editing `.env`:

```bash
python scripts/ingest_pdf.py
python scripts/ingest_github_discussions.py --all
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/build_index.py --reset
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps streamlit run app.py --server.port 8501
```

Remove `EMBEDDING_DEVICE=mps` on non-Apple-Silicon machines.

### Refresh

```bash
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py
```

Full GitHub refresh:

```bash
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py --full-github
```

### Data Locations

- Source PDFs: `data/raw/`
- Parsed PDF pages: `data/processed/pdf_pages.jsonl`
- Local GitHub Discussions: `data/processed/github_discussions.jsonl`
- Retrieval chunks: `data/processed/chunks.jsonl`
- Chroma vector store: `storage/chroma/`
