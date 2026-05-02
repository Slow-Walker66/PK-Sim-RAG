# OSP Suite 本地 RAG 知识库问答 Demo

这是一个本地运行的 Open Systems Pharmacology Suite 知识库问答工具。它会把本地 PDF 手册和 GitHub Discussions 沉淀到本地，使用 Chroma 向量库检索，再调用 DeepSeek 生成中文或英文答案。

## 适合谁

- 想在本机查询 OSP Suite / PK-Sim / MoBi 手册和 Forum 问答的人。
- 不想把自己的问题和本地资料上传到公开平台的人。
- 希望每周把 GitHub Forum 新问题同步进本地知识库的人。

## 你需要准备什么

1. 一台可以联网的电脑。
2. Python 3.10 或更新版本。
3. DeepSeek API key。
4. GitHub Token，用来读取 Open-Systems-Pharmacology/Forum Discussions。
5. PDF 文件：`data/raw/Open Systems Pharmacology Suite.pdf`。

如果你在中国大陆网络环境下下载 Hugging Face 模型比较慢，建议使用：

```bash
HF_ENDPOINT=https://hf-mirror.com
```

如果你用的是 Apple Silicon Mac，建议使用本机 MPS 加速：

```bash
EMBEDDING_DEVICE=mps
```

## 最简单的 Mac 使用方法

把整个 `osp-rag-demo` 文件夹放在一个固定位置，不要放到回收站或临时目录。

### 第一步：安装

双击：

```text
setup.command
```

它会自动创建 Python 环境并安装依赖。

### 第二步：配置 key

复制 `.env.example` 为 `.env`，然后填写：

```bash
DEEPSEEK_API_KEY=你的 DeepSeek key
GITHUB_TOKEN=你的 GitHub token
```

如果你已经在上一级目录放了 `.env`，也可以继续使用。程序会自动读取当前目录或上级目录的 `.env`。

### 第三步：初始化知识库

双击：

```text
update_knowledge_base.command
```

第一次运行会做三件事：

1. 解析 PDF。
2. 全量抓取 GitHub Discussions。
3. 重建 Chroma 向量索引。

第一次下载 `BAAI/bge-m3` embedding 模型会比较久，几分钟到几十分钟都有可能，取决于网络和电脑性能。

### 第四步：启动网页

双击：

```text
start_demo.command
```

浏览器打开：

```text
http://localhost:8501
```
或者按照下面的做法启动网页：
以后每次使用，不需要重新建库，只需要启动网页。

最简单方式：

双击这个文件：

osp-rag-demo/start_demo.command

它会自动进入项目、设置 Hugging Face 镜像、启用 Mac MPS 加速，然后启动 Streamlit。

如果你想用终端启动，就输入：

bash



cd /Users/walker/PK-Sim/osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps ../.venv/bin/streamlit run app.py --server.port 8501



每周更新 GitHub 新 discussion 时，双击：

osp-rag-demo/update_knowledge_base.command

或者终端运行：

bash



cd /Users/walker/PK-Sim/osp-rag-demo
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps ../.venv/bin/python scripts/update_knowledge_base.py



日常使用流程就是：

双击 start_demo.command
打开 http://localhost:8501
提问

只有每周同步新内容时才运行 update_knowledge_base.command。

## 命令行使用方法

如果你熟悉终端，也可以这样运行。

```bash
cd osp-rag-demo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

解析 PDF：

```bash
python scripts/ingest_pdf.py
```

全量抓取 GitHub Discussions：

```bash
python scripts/ingest_github_discussions.py --all
```

构建索引：

```bash
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/build_index.py --reset
```

启动网页：

```bash
HF_ENDPOINT=https://hf-mirror.com streamlit run app.py
```

## 每周更新知识库

推荐每周运行一次：

```bash
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py
```

这个命令默认只抓取 GitHub 上本地库之后更新过的 discussions，然后重建索引。

如果你想重新全量同步 GitHub：

```bash
HF_ENDPOINT=https://hf-mirror.com EMBEDDING_DEVICE=mps python scripts/update_knowledge_base.py --full-github
```

Mac 用户也可以每周双击：

```text
update_knowledge_base.command
```

## 测试检索

中文测试：

```bash
HF_ENDPOINT=https://hf-mirror.com python scripts/test_retrieval.py "Parameter Identification 有哪三种 optimization algorithms？它们有什么区别？" --min-score 0.55
```

英文测试：

```bash
HF_ENDPOINT=https://hf-mirror.com python scripts/test_retrieval.py "How do I install Open Systems Pharmacology Suite?" --min-score 0.70
```

无关问题测试：

```bash
HF_ENDPOINT=https://hf-mirror.com python scripts/test_retrieval.py "量子香蕉蛋糕食谱和火星旅游签证怎么办？" --min-score 0.70
```

如果没有足够相关内容，会输出：

```text
当前知识库暂无足够相关内容
```

## 配置说明

主要配置都在 `.env`：

```bash
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

GITHUB_TOKEN=github_pat_or_classic_token
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

建议：

- `MIN_RELEVANCE_SCORE`：一般用 `0.65` 到 `0.75`。越高越保守，越不容易乱答。
- `TOP_K`：一般用 `8`。
- `EMBEDDING_DEVICE`：Apple Silicon Mac 建议填 `mps`；其他电脑可以留空。
- `PDF_WINDOW_PAGES`：默认 `1`。索引保持轻量，避免初始化过慢。
- `PDF_CONTEXT_PAGES`：默认 `4`。检索命中某一页后，会自动把前后 4 页一起放入回答上下文，解决手册内容跨页的问题。
- `MAX_CONTEXT_CHARS`：默认 `18000`，给 DeepSeek 更多上下文。

## 数据和索引在哪里

- PDF 原文：`data/raw/`
- PDF 解析结果：`data/processed/pdf_pages.jsonl`
- GitHub Discussions 本地库：`data/processed/github_discussions.jsonl`
- 合并后的检索 chunks：`data/processed/chunks.jsonl`
- Chroma 向量库：`storage/chroma/`

这些文件都在本机。删除 `storage/chroma/` 后可以重新运行 `build_index.py --reset` 生成索引。

## RAG 行为约束

- 用户用中文问，回答中文；用户用英文问，回答英文。
- DeepSeek 只能基于检索到的上下文回答。
- 回答必须带 `[S1]`、`[S2]` 这样的引用。
- PDF 引用会显示文件名、页码和原文摘录。
- GitHub 引用会显示 discussion 标题、链接、原始问题和相关回答摘要。
- 如果检索结果不够相关，必须返回 `当前知识库暂无足够相关内容`。

## 常见问题

### 模型下载卡住

使用镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

或直接在命令前加：

```bash
HF_ENDPOINT=https://hf-mirror.com python scripts/build_index.py --reset
```

### 网页打开后没有答案

检查 `.env` 里是否有：

```bash
DEEPSEEK_API_KEY=...
```

### GitHub 抓取失败

检查：

```bash
GITHUB_TOKEN=...
GITHUB_OWNER=Open-Systems-Pharmacology
GITHUB_REPO=Forum
```

GitHub token 至少要能读取公开仓库 discussions。

### 回答说知识库内容不足

可以先把网页侧栏里的“最低相关性阈值”降低到 `0.55` 试试。对于很具体的问题，建议换一种问法，把英文术语一起写上，例如：

```text
Parameter Identification optimization algorithms Monte-Carlo Levenberg-Marquardt Nelder-Mead
```
