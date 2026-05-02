from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from config import settings
from rag.answer_generator import AnswerGenerator
from rag.deepseek_client import DeepSeekClient
from rag.embeddings import EmbeddingModel
from rag.prompts import INSUFFICIENT_MESSAGE
from rag.retriever import Retriever
from rag.vector_store import ChromaVectorStore


PROJECT_DIR = Path(__file__).resolve().parent
BRAND_IMAGE = PROJECT_DIR / "assets/pksim_notes_qr.jpg"


st.set_page_config(
    page_title="OSP Suite Local RAG",
    layout="wide",
)


st.markdown(
    """
    <style>
    :root {
      --osp-ink: #17202a;
      --osp-muted: #607080;
      --osp-line: #d8e0e7;
      --osp-panel: #ffffff;
      --osp-blue: #0c6f9f;
      --osp-green: #2b8a6e;
      --osp-amber: #b26a00;
    }
    .stApp {
      background: linear-gradient(180deg, #f5f8fb 0%, #eef4f1 100%);
      color: var(--osp-ink);
    }
    [data-testid="stSidebar"] {
      background: #ffffff;
      border-right: 1px solid var(--osp-line);
    }
    [data-testid="stSidebar"] img {
      border: 1px solid var(--osp-line);
      border-radius: 8px;
    }
    .osp-header {
      border: 1px solid var(--osp-line);
      border-radius: 8px;
      padding: 18px 20px;
      background: rgba(255, 255, 255, 0.92);
      margin-bottom: 14px;
    }
    .osp-kicker {
      color: var(--osp-green);
      font-weight: 700;
      font-size: 0.82rem;
      letter-spacing: 0;
      text-transform: uppercase;
    }
    .osp-title {
      margin: 4px 0 4px 0;
      color: var(--osp-ink);
      font-size: 2rem;
      line-height: 1.16;
      font-weight: 760;
    }
    .osp-subtitle {
      color: var(--osp-muted);
      font-size: 0.98rem;
      margin: 0;
    }
    .osp-answer {
      border-left: 4px solid var(--osp-blue);
      padding: 4px 0 4px 14px;
    }
    .osp-source-title {
      color: var(--osp-muted);
      font-size: 0.9rem;
      margin-bottom: 4px;
    }
    div[data-testid="stMetric"] {
      background: #ffffff;
      border: 1px solid var(--osp-line);
      border-radius: 8px;
      padding: 10px 12px;
    }
    div[data-testid="stExpander"] {
      border: 1px solid var(--osp-line);
      border-radius: 8px;
      background: #ffffff;
    }
    .stButton > button, .stFormSubmitButton > button {
      border-radius: 7px;
      border: 1px solid #0c6f9f;
      font-weight: 700;
    }
    textarea {
      border-radius: 8px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore(settings.vector_db_dir, settings.collection_name)


@st.cache_resource(show_spinner=False)
def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel(settings.embedding_model, device=settings.embedding_device)


@st.cache_resource(show_spinner=False)
def get_answer_generator() -> AnswerGenerator:
    vector_store = get_vector_store()
    retriever = Retriever(
        get_embedding_model(),
        vector_store,
        pdf_pages_path=settings.pdf_pages_path,
        pdf_context_pages=settings.pdf_context_pages,
    )
    deepseek = DeepSeekClient(
        settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )
    return AnswerGenerator(retriever, deepseek, max_context_chars=settings.max_context_chars)


def _page_label(meta: dict) -> str:
    start = meta.get("page_start", "")
    end = meta.get("page_end", "")
    if end and end != start:
        return f"{start}-{end}"
    return str(start)


def _source_heading(index: int, chunk) -> str:
    meta = chunk.metadata
    if meta.get("source_type") == "pdf":
        return f"[S{index}] PDF · {meta.get('file_name', '')} · pages {_page_label(meta)}"
    if meta.get("source_type") == "github_discussion":
        return f"[S{index}] GitHub · #{meta.get('discussion_number', '')} · {meta.get('title', '')}"
    return f"[S{index}] Source"


def _show_citation(index: int, chunk) -> None:
    meta = chunk.metadata
    source_type = meta.get("source_type")

    with st.expander(_source_heading(index, chunk), expanded=index <= 2):
        if source_type == "pdf":
            st.caption(
                f"score={chunk.score:.3f} · section={meta.get('section', '')} · "
                f"strategy={meta.get('chunk_strategy', '')}"
            )
            st.code(chunk.text[:2600], language="text")
            return

        if source_type == "github_discussion":
            title = html.escape(meta.get("title", "GitHub Discussion"))
            link = meta.get("comment_url") or meta.get("url") or ""
            if link:
                st.markdown(f"**Discussion:** [{title}]({link})")
            st.caption(
                f"score={chunk.score:.3f} · role={meta.get('source_role', '')} · "
                f"category={meta.get('category', '')}"
            )
            if meta.get("question_text"):
                st.markdown("**原始问题**")
                st.write(meta.get("question_text"))
            if meta.get("answer_summary"):
                st.markdown("**相关回答摘要 / 摘录**")
                st.write(meta.get("answer_summary"))
            st.markdown("**原始参考摘录**")
            st.code(chunk.text[:2600], language="text")
            return

        st.caption(f"score={chunk.score:.3f}")
        st.code(chunk.text[:2600], language="text")


def _run_question(question: str, top_k: int, min_score: float) -> None:
    with st.spinner("正在检索本地知识库并生成答案..."):
        result = get_answer_generator().answer(question, top_k=top_k, min_score=min_score)
    st.session_state.history.insert(0, (question, result))


with st.sidebar:
    if BRAND_IMAGE.exists():
        st.image(str(BRAND_IMAGE), caption="PKsim 学习笔记", use_container_width=True)
    st.subheader("本地知识库")
    try:
        count = get_vector_store().count()
    except Exception as exc:
        count = 0
        st.error(f"向量库加载失败：{exc}")

    st.metric("索引片段", f"{count:,}")
    st.write(f"Embedding: `{settings.embedding_model}`")
    st.write(f"DeepSeek: `{settings.deepseek_model}`")
    st.write(f"PDF 补页: `±{settings.pdf_context_pages}` pages")

    st.divider()
    top_k = st.slider("Top K", min_value=1, max_value=20, value=settings.top_k)
    default_min_score = max(float(settings.min_relevance_score), 0.50)
    min_score = st.slider(
        "最低相关性阈值",
        min_value=0.0,
        max_value=1.0,
        value=default_min_score,
        step=0.01,
    )

    st.divider()
    if st.button("清空当前会话", use_container_width=True):
        st.session_state.history = []
        st.rerun()


header_left, header_right = st.columns([0.76, 0.24], vertical_alignment="center")
with header_left:
    st.markdown(
        """
        <div class="osp-header">
          <div class="osp-kicker">Open Systems Pharmacology Suite</div>
          <div class="osp-title">本地知识库问答</div>
          <p class="osp-subtitle">PDF 手册与 GitHub Discussions 的私有检索增强问答</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with header_right:
    if BRAND_IMAGE.exists():
        st.image(str(BRAND_IMAGE), use_container_width=True)

if not settings.deepseek_api_key:
    st.warning("未检测到 DEEPSEEK_API_KEY。请先在 .env 中配置 DeepSeek API key。")

if "history" not in st.session_state:
    st.session_state.history = []

with st.container(border=True):
    with st.form("question_form"):
        question = st.text_area(
            "问题",
            height=128,
            placeholder="例如：Parameter Identification 有哪三种 optimization algorithms？它们有什么区别？",
        )
        submitted = st.form_submit_button("检索并生成答案", type="primary", use_container_width=True)

    example_cols = st.columns(3)
    examples = [
        "Parameter Identification 有哪三种 optimization algorithms？它们有什么区别？",
        "How do I install Open Systems Pharmacology Suite?",
        "PK-Sim 如何处理 LLOQ values?",
    ]
    for col, example in zip(example_cols, examples):
        if col.button(example, use_container_width=True):
            _run_question(example, top_k, min_score)
            st.rerun()

if submitted:
    question = question.strip()
    if not question:
        st.info("请先输入问题。")
    else:
        try:
            _run_question(question, top_k, min_score)
            st.rerun()
        except Exception as exc:
            st.error(f"执行失败：{exc}")

for question, result in st.session_state.history:
    with st.container(border=True):
        st.markdown("**问题**")
        st.write(question)
        st.markdown('<div class="osp-answer">', unsafe_allow_html=True)
        st.markdown("**答案**")
        if result.answer.strip() == INSUFFICIENT_MESSAGE:
            st.warning(result.answer)
        else:
            st.markdown(result.answer)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="osp-source-title">引用来源</div>', unsafe_allow_html=True)
        if not result.citations:
            st.info("没有达到阈值的检索结果。")
        else:
            for index, citation in enumerate(result.citations, start=1):
                _show_citation(index, citation)
