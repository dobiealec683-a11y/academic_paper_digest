from __future__ import annotations

import streamlit as st
import pandas as pd
from openalex_client import OpenAlexClient
from paper_ranker import rank_papers
from pdf_collector import PDFCollector
from notebooklm_bridge import NotebookLMBridge
from digest_builder import DigestBuilder
from telegram_sender import send_digest_telegram
from prompts import (
    PROMPT_PER_PAPER_EXTRACTION,
    PROMPT_CROSS_PAPER_SYNTHESIS,
    PROMPT_EXECUTIVE_DIGEST,
    PROMPT_RESEARCH_MAP
)
import config
from run_history import RunHistory
from utils import configure_logging, topic_slug

configure_logging(config.LOG_LEVEL, config.LOGS_DIR / "pipeline.log")
history = RunHistory()

# Page Config
st.set_page_config(
    page_title="Academic Research Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    .reportview-container {
        background: #0f111a;
    }
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #1E293B;
    }
    .stButton>button {
        background-color: #4F46E5;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #4338CA;
        transform: translateY(-1px);
    }
    .card {
        padding: 20px;
        border-radius: 12px;
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "ranked_df" not in st.session_state:
    st.session_state.ranked_df = None
if "downloaded_df" not in st.session_state:
    st.session_state.downloaded_df = None
if "failed_df" not in st.session_state:
    st.session_state.failed_df = None
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "notebook_id" not in st.session_state:
    st.session_state.notebook_id = None
if "synthesis_done" not in st.session_state:
    st.session_state.synthesis_done = False

# Sidebar Configuration & Parameters
with st.sidebar:
    st.title("⚙️ Control Panel")
    
    st.subheader("NotebookLM Mode")
    mode_option = st.selectbox(
        "Bridge Mode",
        options=["mock", "notebooklm_py", "enterprise"],
        index=0,
        help="Select 'mock' for local prototyping. Use 'notebooklm_py' for unofficial CLI, or 'enterprise' for GCP API."
    )
    config.NOTEBOOKLM_MODE = mode_option
    
    st.subheader("OpenAlex Credentials")
    openalex_email = st.text_input("OpenAlex Email", value=config.OPENALEX_EMAIL)
    config.OPENALEX_EMAIL = openalex_email

    st.markdown("---")
    st.markdown("### Output Directories")
    st.code(f"PDFs: {config.PDFS_DIR.name}\nMetadata: {config.METADATA_DIR.name}\nDigests: {config.DIGESTS_DIR.name}")

# Main Header
st.title("🎓 Academic Research Assistant Pipeline")
st.caption("A source-grounded orchestrator using OpenAlex for discovery, PDF downloading, and NotebookLM for synthesis.")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Discovery & Ranking", 
    "📥 Ingestion & Collection", 
    "🧪 NotebookLM Orchestrator", 
    "📊 Research Dashboard"
])

# Tab 1: Discovery & Ranking
with tab1:
    st.header("Search & Discover Literature")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        query = st.text_input("Research Topic / Search Query", placeholder="e.g. self-attention models transformer scalability", value=st.session_state.topic)
    with col2:
        start_year = st.number_input("Start Year", min_value=1950, max_value=2030, value=2015)
    with col3:
        max_results = st.slider("Max Results", min_value=5, max_value=50, value=15)
        
    col1_sub, col2_sub = st.columns(2)
    with col1_sub:
        open_access_only = st.checkbox("Open-Access Only", value=False)
    with col2_sub:
        sort_by = st.selectbox("Sort By", options=["cited_by_count:desc", "publication_date:desc", "relevance_score:desc"], index=0)

    if st.button("🚀 Execute Discovery & Ranking"):
        if not query.strip():
            st.error("Please enter a research topic query.")
        else:
            with st.spinner("Searching OpenAlex and applying multi-criteria scoring algorithm..."):
                client = OpenAlexClient(email=openalex_email)
                results = client.search_works(
                    query=query,
                    start_year=int(start_year),
                    max_results=max_results,
                    open_access_only=open_access_only,
                    sort_by=sort_by
                )
                
                if results:
                    st.session_state.topic = query
                    st.session_state.search_results = results
                    st.session_state.ranked_df = rank_papers(results, query)
                    history.append("dashboard_discover", status="succeeded", topic=query, details={"results": len(results)})
                    st.success(f"Discovered and scored {len(results)} papers successfully!")
                else:
                    history.append("dashboard_discover", status="succeeded", topic=query, details={"results": 0})
                    st.warning("No papers matching the criteria were found.")

    if st.session_state.ranked_df is not None:
        st.subheader("🏆 Ranked & Scored Results")
        st.markdown("Papers are ranked using keyword relevance, citations, recency, open-access, and PDF availability.")
        
        # Display clean view
        display_df = st.session_state.ranked_df[[
            "rank", "total_score", "title", "year", "citations", "journal_source", "reason_selected", "pdf_url"
        ]].copy()
        
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "pdf_url": st.column_config.LinkColumn("PDF Link")
            }
        )

# Tab 2: Ingestion & Collection
with tab2:
    st.header("PDF and Companion Source Ingestor")
    
    if st.session_state.ranked_df is None:
        st.info("Please run discovery in the first tab to discover papers.")
    else:
        st.markdown("Generate companion markdown metadata files for all papers and download open-access PDFs when direct links are available.")
        
        if st.button("📥 Download & Collect Ingestion Package"):
            with st.spinner("Downloading PDFs and generating companion metadata markdown files..."):
                collector = PDFCollector()
                df_dl, df_fail = collector.collect_sources(st.session_state.topic, st.session_state.ranked_df)
                history.append(
                    "dashboard_collect",
                    status="succeeded",
                    topic=st.session_state.topic,
                    details={"downloaded": len(df_dl), "failed": len(df_fail)},
                )
                
                st.session_state.downloaded_df = df_dl
                st.session_state.failed_df = df_fail
                
                st.success(f"Ingestion Package Compiled! Saved under `outputs/pdfs/{st.session_state.topic.lower().replace(' ', '_')}`")
        
        if st.session_state.downloaded_df is not None:
            col_dl, col_fl = st.columns(2)
            with col_dl:
                st.subheader("✅ Successful Downloads")
                st.dataframe(st.session_state.downloaded_df[["rank", "title", "year", "local_pdf_path"]], use_container_width=True)
            with col_fl:
                st.subheader("❌ Missing / Failed PDFs (Metadata Ingested)")
                st.dataframe(st.session_state.failed_df[["rank", "title", "error"]], use_container_width=True)

# Tab 3: NotebookLM Orchestrator
with tab3:
    st.header("🧠 NotebookLM Grounded Synthesis Bridge")
    st.caption(f"Currently configured mode: **{config.NOTEBOOKLM_MODE.upper()}**")
    
    if st.session_state.ranked_df is None:
        st.info("Please search and discover papers to ingest.")
    else:
        col_nb1, col_nb2 = st.columns(2)
        with col_nb1:
            st.subheader("Step 1: Notebook Setup & Uploads")
            
            # Show number of files ready to upload
            slug = topic_slug(st.session_state.topic)
            meta_path = config.METADATA_DIR / slug
            pdf_path = config.PDFS_DIR / slug
            
            num_meta = len(list(meta_path.glob("*.md"))) if meta_path.exists() else 0
            num_pdf = len(list(pdf_path.glob("*.pdf"))) if pdf_path.exists() else 0
            
            st.markdown(f"""
            - **Ready Metadata Ingestion Files (.md):** {num_meta}
            - **Ready PDF Articles (.pdf):** {num_pdf}
            """)
            
            if st.button("🛠️ Create Notebook & Upload Sources"):
                with st.spinner("Connecting to NotebookLM & Uploading files..."):
                    bridge = NotebookLMBridge()
                    nb_id = bridge.create_notebook(st.session_state.topic)
                    st.session_state.notebook_id = nb_id
                    
                    # Batch upload paths
                    sources_to_upload = []
                    if meta_path.exists():
                        sources_to_upload.extend(list(meta_path.glob("*.md")))
                    if pdf_path.exists():
                        sources_to_upload.extend(list(pdf_path.glob("*.pdf")))
                        
                    bridge.batch_add_sources(nb_id, sources_to_upload)
                    history.append(
                        "dashboard_upload_sources",
                        status="succeeded",
                        topic=st.session_state.topic,
                        details={"notebook_id": nb_id, "sources": len(sources_to_upload)},
                    )
                    st.success(f"Notebook Created and Ingested successfully! ID: `{nb_id}`")
                    
        with col_nb2:
            st.subheader("Step 2: Trigger Structured Prompts")
            if st.session_state.notebook_id is None:
                st.warning("Please setup a notebook in Step 1 first.")
            else:
                st.markdown("Instruct NotebookLM to generate grounded, source-cited digests:")
                
                if st.button("🧠 Generate Grounded Syntheses"):
                    with st.spinner("Running structured prompts on NotebookLM..."):
                        bridge = NotebookLMBridge()
                        nb_id = st.session_state.notebook_id
                        
                        # 1. Per-paper extraction
                        bridge.ask_notebook(nb_id, PROMPT_PER_PAPER_EXTRACTION, f"{slug}_extraction.md")
                        # 2. Cross-paper synthesis
                        bridge.ask_notebook(nb_id, PROMPT_CROSS_PAPER_SYNTHESIS, f"{slug}_synthesis.md")
                        # 3. Executive digest
                        bridge.ask_notebook(nb_id, PROMPT_EXECUTIVE_DIGEST, f"{slug}_digest.md")
                        # 4. Research Map
                        bridge.ask_notebook(nb_id, PROMPT_RESEARCH_MAP, f"{slug}_map.md")
                        
                        # Build digests
                        builder = DigestBuilder()
                        df_dl = st.session_state.downloaded_df if st.session_state.downloaded_df is not None else pd.DataFrame()
                        builder.build_digests(st.session_state.topic, df_dl)
                        history.append("dashboard_synthesize", status="succeeded", topic=st.session_state.topic)
                        
                        st.session_state.synthesis_done = True
                        st.success("All grounded syntheses generated and digests compiled successfully!")

# Tab 4: Research Dashboard & Digest Viewer
with tab4:
    st.header("📊 Grounded Literature Digest & Analysis")
    
    if not st.session_state.synthesis_done:
        st.info("Please generate syntheses in the 'NotebookLM Orchestrator' tab to view results.")
    else:
        slug = topic_slug(st.session_state.topic)
        
        # Read the generated files
        digest_file = config.DIGESTS_DIR / f"{slug}_daily_digest.md"
        brief_file = config.DIGESTS_DIR / f"{slug}_executive_brief.md"
        map_file = config.DIGESTS_DIR / f"{slug}_research_map.md"
        lit_table_file = config.DIGESTS_DIR / f"{slug}_literature_table.csv"
        
        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
            "📰 Daily Digest", 
            "📋 Executive Brief", 
            "🗺️ Research Map", 
            "📊 Literature Table"
        ])
        
        with sub_tab1:
            if digest_file.exists():
                st.markdown(digest_file.read_text(encoding="utf-8"))
        
        with sub_tab2:
            if brief_file.exists():
                st.markdown(brief_file.read_text(encoding="utf-8"))
                
        with sub_tab3:
            if map_file.exists():
                st.markdown(map_file.read_text(encoding="utf-8"))
                
        with sub_tab4:
            if lit_table_file.exists():
                df_lit = pd.read_csv(lit_table_file)
                st.dataframe(df_lit, use_container_width=True)
                
        # Export downloads
        st.subheader("💾 Export Deliverables")
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        with col_ex1:
            if digest_file.exists():
                st.download_button(
                    label="Download Daily Digest",
                    data=digest_file.read_text(encoding="utf-8"),
                    file_name=f"{slug}_daily_digest.md",
                    mime="text/markdown"
                )
        with col_ex2:
            if brief_file.exists():
                st.download_button(
                    label="Download Executive Brief",
                    data=brief_file.read_text(encoding="utf-8"),
                    file_name=f"{slug}_executive_brief.md",
                    mime="text/markdown"
                )
        with col_ex3:
            if lit_table_file.exists():
                st.download_button(
                    label="Download Literature Table CSV",
                    data=lit_table_file.read_text(encoding="utf-8"),
                    file_name=f"{slug}_literature_table.csv",
                    mime="text/csv"
                )

        st.subheader("Telegram Digest")
        if st.button("Send to Telegram"):
            try:
                attachments = send_digest_telegram(st.session_state.topic)
                history.append(
                    "dashboard_telegram_digest",
                    status="succeeded",
                    topic=st.session_state.topic,
                    details={"attachments": [str(path) for path in attachments]},
                )
                st.success(f"Sent digest preview and {len(attachments)} files to Telegram.")
            except Exception as exc:
                history.append(
                    "dashboard_telegram_digest",
                    status="failed",
                    topic=st.session_state.topic,
                    details={"error": str(exc)},
                )
                st.error(str(exc))
