"""
Healthcare Payer-Provider Negotiation Intelligence Dashboard
=============================================================

Streamlit app showing:
  - Live chain-of-thought as Ollama analyzes each article
  - Tri-state (NY/CT/NJ) provider and regulation breakdowns
  - Inferred payer perspectives for Cigna, United, Anthem
  - Filterable results by state, payer, negotiation type
  - Knowledge base panels for providers and regulations

Run:  uv run streamlit run app/dashboard.py
"""
from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

from app.knowledge import (
    PROVIDERS, PAYERS, STATE_REGULATIONS,
    PAYER_INFERENCE_PROMPTS, OLLAMA_MODEL,
)
from app.fetcher import fetch_all, Article
from app.analyzer import (
    analyze_batch, check_ollama, AnalysisResult, ThoughtStep,
)
from app.persistence import (
    load_seen,
    save_seen,
    filter_unseen,
    mark_seen,
    load_analysis_runs,
    save_analysis_runs,
    append_analysis_run,
    materialize_run,
)

# ─── Page config ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="Healthcare Negotiation Monitor",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session state init ─────────────────────────────────────────────

if "results" not in st.session_state:
    st.session_state.results = []
if "thoughts" not in st.session_state:
    st.session_state.thoughts = []
if "running" not in st.session_state:
    st.session_state.running = False
if "last_run" not in st.session_state:
    st.session_state.last_run = None
if "analysis_runs" not in st.session_state:
    st.session_state.analysis_runs = load_analysis_runs()
if "hydrated_from_disk" not in st.session_state:
    st.session_state.hydrated_from_disk = True
    if st.session_state.analysis_runs and not st.session_state.results:
        th0, res0 = materialize_run(st.session_state.analysis_runs[0])
        st.session_state.thoughts = th0
        st.session_state.results = res0
        st.session_state.last_run = st.session_state.analysis_runs[0].get("label")

# Apply any deferred widget state updates BEFORE widgets render.
if "_defer_view_saved_run" in st.session_state:
    st.session_state.view_saved_run = int(st.session_state._defer_view_saved_run)
    del st.session_state["_defer_view_saved_run"]
if "_defer_view_mode" in st.session_state:
    st.session_state.view_mode = str(st.session_state._defer_view_mode)
    del st.session_state["_defer_view_mode"]


# ─── Sidebar: Controls & Knowledge Base ──────────────────────────────

with st.sidebar:
    st.title("🏥 Negotiation Monitor")
    st.caption("Tri-State Provider-Payer Intelligence")

    # Ollama status
    ok, msg = check_ollama()
    if ok:
        st.success(f"✅ Ollama: {OLLAMA_MODEL}", icon="🤖")
    else:
        st.error(f"❌ {msg}")

    st.divider()

    # Run controls
    run_payer_inf = st.toggle("Run payer perspective inference", value=True,
                              help="Generate Cigna/United/Anthem strategic perspectives for each article")

    if st.button("🔄 Run Scan Now", type="primary", use_container_width=True,
                 disabled=st.session_state.running or not ok):
        st.session_state.running = True
        st.rerun()

    if st.session_state.last_run:
        st.caption(f"Last run: {st.session_state.last_run}")

    if st.session_state.analysis_runs:
        st.subheader("🕘 Run History")
        view_mode = st.radio(
            "Display",
            ["Current session", "Saved run"],
            horizontal=True,
            key="view_mode",
            disabled=st.session_state.running,
            help="Switch between the current session's results and a previously saved run.",
        )

        n = len(st.session_state.analysis_runs)

        def _run_label(i: int) -> str:
            r = st.session_state.analysis_runs[i]
            na = len(r.get("results") or [])
            return f"{r.get('label', '?')} ({na} articles)"

        sel_idx = st.selectbox(
            "Select run",
            options=list(range(n)),
            format_func=_run_label,
            key="view_saved_run",
            disabled=st.session_state.running,
        )

        if view_mode == "Saved run":
            prev_idx = st.session_state.get("_last_viewed_run_idx")
            if prev_idx != sel_idx:
                st.session_state._last_viewed_run_idx = sel_idx
                th, res = materialize_run(st.session_state.analysis_runs[sel_idx])
                st.session_state.thoughts = th
                st.session_state.results = res
                st.session_state.last_run = st.session_state.analysis_runs[sel_idx].get("label")
    else:
        st.caption("No saved runs yet — run a scan to create history.")

    st.divider()

    # Knowledge base navigation
    st.subheader("📚 Knowledge Base")
    kb_tab = st.radio("Section", ["Providers", "Payers", "Regulations"],
                      label_visibility="collapsed")

    if kb_tab == "Providers":
        state_sel = st.selectbox("State", ["NY", "CT", "NJ"])
        for p in PROVIDERS.get(state_sel, []):
            with st.expander(f"🏥 {p['name']} ({p['type']})"):
                st.markdown(f"**Beds:** {p['beds']:,}")
                st.markdown(f"**Notes:** {p['notes']}")
                st.markdown(f"**Aliases:** {', '.join(p['aliases'])}")

    elif kb_tab == "Payers":
        for pname, pinfo in PAYERS.items():
            states_str = ", ".join(pinfo["states"])
            with st.expander(f"💳 {pname} ({states_str})"):
                st.markdown(f"**Segments:** {', '.join(pinfo['segments'])}")
                st.markdown(f"**Notes:** {pinfo['notes']}")
                if pname in PAYER_INFERENCE_PROMPTS:
                    st.caption("🧠 Payer perspective inference enabled")

    elif kb_tab == "Regulations":
        state_sel2 = st.selectbox("State", ["NY", "CT", "NJ"], key="reg_state")
        reg = STATE_REGULATIONS[state_sel2]
        st.markdown(f"**{reg['summary']}**")
        st.markdown("**Key Rules:**")
        for rule in reg["key_rules"]:
            st.markdown(f"- {rule}")
        st.markdown("**Regulators:**")
        for r in reg["regulators"]:
            st.markdown(f"- {r}")


# ─── Helper: severity badge ─────────────────────────────────────────

def severity(score: int) -> str:
    if score >= 9: return "🔴"
    if score >= 7: return "🟠"
    return "🟡"

def type_label(t: str) -> str:
    return {
        "contract_dispute": "Contract Dispute",
        "network_exit": "Network Exit",
        "rate_negotiation": "Rate Negotiation",
        "regulatory_change": "Regulatory Change",
        "market_consolidation": "Market Consolidation",
        "enrollment_impact": "Enrollment Impact",
        "policy_update": "Policy Update",
        "other": "General",
    }.get(t, t.replace("_", " ").title())


# ─── Main content area ──────────────────────────────────────────────

tab_live, tab_results, tab_states, tab_payers = st.tabs([
    "🔴 Live Chain of Thought",
    "📊 Results",
    "🗺️ State Breakdown",
    "🧠 Payer Perspectives",
])


# ─── TAB: Live Chain of Thought ─────────────────────────────────────

with tab_live:
    thought_container = st.container()

    if st.session_state.running:
        with thought_container:
            st.subheader("🔴 Live Analysis in Progress")
            progress_bar = st.progress(0, text="Starting...")
            thought_log = st.container(height=500)
            status_text = st.empty()

            # Collect thoughts
            thoughts: list[ThoughtStep] = []

            def on_thought(step: ThoughtStep):
                thoughts.append(step)
                phase_emoji = {"fetch": "📥", "analyze": "🔍", "payer_inference": "🧠"}.get(step.phase, "•")
                payer_tag = f" [{step.payer_name}]" if step.payer_name else ""
                with thought_log:
                    st.markdown(
                        f"`{phase_emoji}{payer_tag}` **{step.article_title[:50]}** — {step.message}"
                    )

            def on_fetch_status(msg: str):
                status_text.text(msg)

            # Step 1: Fetch
            status_text.text("Fetching articles from all sources...")
            progress_bar.progress(5, text="Fetching...")
            articles = fetch_all(on_status=on_fetch_status)

            # Step 2: Dedup
            status_text.text("Deduplicating...")
            progress_bar.progress(15, text="Deduplicating...")
            seen_db = load_seen()
            new_articles = filter_unseen(articles, seen_db)

            if not new_articles:
                status_text.text("✅ No new articles to analyze.")
                progress_bar.progress(100, text="Done — no new articles")
                st.session_state.running = False
                st.session_state.last_run = datetime.now().strftime("%H:%M:%S")
            else:
                status_text.text(f"Analyzing {len(new_articles)} new articles...")
                progress_bar.progress(20, text=f"Analyzing {len(new_articles)} articles...")

                # Step 3: Analyze
                results = analyze_batch(
                    new_articles,
                    on_thought=on_thought,
                    run_payer_inference=run_payer_inf,
                )

                # Step 4: Save
                seen_db = mark_seen(new_articles, seen_db)
                save_seen(seen_db)

                st.session_state.results = results
                st.session_state.thoughts = thoughts
                st.session_state.running = False
                st.session_state.last_run = datetime.now().strftime("%H:%M:%S")

                record = append_analysis_run(thoughts, results)
                st.session_state.analysis_runs = [record] + st.session_state.analysis_runs[:24]
                save_analysis_runs(st.session_state.analysis_runs)
                st.session_state._last_viewed_run_idx = 0
                # Defer widget state updates to next rerun (Streamlit restriction).
                st.session_state._defer_view_saved_run = 0
                st.session_state._defer_view_mode = "Current session"

                progress_bar.progress(100, text=f"Done — {len(results)} results above threshold")
                status_text.text(f"✅ Complete. {len(results)} articles scored above threshold.")

    else:
        with thought_container:
            if st.session_state.thoughts:
                st.subheader("📜 Chain of Thought (Last Run)")
                log = st.container(height=500)
                for step in st.session_state.thoughts:
                    phase_emoji = {"fetch": "📥", "analyze": "🔍", "payer_inference": "🧠"}.get(step.phase, "•")
                    payer_tag = f" [{step.payer_name}]" if step.payer_name else ""
                    with log:
                        st.markdown(
                            f"`{phase_emoji}{payer_tag}` **{step.article_title[:50]}** — {step.message}"
                        )
                        if step.raw_response:
                            with st.expander("Raw LLM response"):
                                st.code(step.raw_response, language="text")
            else:
                st.info("Click **Run Scan Now** in the sidebar to start monitoring.")


# ─── TAB: Results ────────────────────────────────────────────────────

with tab_results:
    results = st.session_state.results

    if not results:
        st.info("No results yet. Run a scan to populate.")
    else:
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            state_filter = st.multiselect("State", ["NY", "CT", "NJ"], default=["NY", "CT", "NJ"])
        with col_f2:
            types = sorted(set(r.negotiation_type for r in results))
            type_filter = st.multiselect("Type", types, default=types,
                                          format_func=type_label)
        with col_f3:
            min_score = st.slider("Min score", 1, 10, 5)

        filtered = [
            r for r in results
            if r.relevance_score >= min_score
            and r.negotiation_type in type_filter
            and (not r.states_affected or any(s in state_filter for s in r.states_affected)
                 or not r.states_affected)
        ]

        st.markdown(f"**{len(filtered)}** articles matching filters")

        for r in filtered:
            states_str = " ".join(f"`{s}`" for s in r.states_affected) if r.states_affected else "`National`"
            with st.expander(
                f"{severity(r.relevance_score)} [{r.relevance_score}/10] "
                f"{r.article.title[:80]} — {states_str}"
            ):
                st.markdown(f"**Source:** {r.article.source} | "
                            f"**Type:** {type_label(r.negotiation_type)}")
                if r.parties:
                    st.markdown(f"**Parties:** {', '.join(r.parties)}")
                st.markdown(r.summary)
                if r.key_insight:
                    st.info(f"💡 {r.key_insight}")
                if r.action_signals:
                    st.markdown("**Action Signals:**")
                    for sig in r.action_signals:
                        st.markdown(f"- {sig}")
                if r.chain_of_thought:
                    with st.expander("🧠 Chain of thought"):
                        st.markdown(r.chain_of_thought)
                st.link_button("Open article →", r.article.url)


# ─── TAB: State Breakdown ───────────────────────────────────────────

with tab_states:
    results = st.session_state.results

    for state in ["NY", "CT", "NJ"]:
        state_results = [r for r in results if state in (r.states_affected or [])]
        state_name = {"NY": "New York", "CT": "Connecticut", "NJ": "New Jersey"}[state]

        st.subheader(f"{'🗽' if state == 'NY' else '🌲' if state == 'CT' else '🏖️'} {state_name}")

        col_a, col_b = st.columns([2, 1])

        with col_a:
            if state_results:
                for r in state_results[:5]:
                    st.markdown(
                        f"{severity(r.relevance_score)} **{r.article.title[:70]}** "
                        f"({type_label(r.negotiation_type)})"
                    )
                    if r.key_insight:
                        st.caption(r.key_insight)
            else:
                st.caption("No state-specific articles this cycle.")

        with col_b:
            reg = STATE_REGULATIONS[state]
            st.markdown(f"**Regulatory context:**")
            st.caption(reg["summary"])
            # Show top 3 rules
            for rule in reg["key_rules"][:3]:
                st.caption(f"• {rule}")

        st.divider()


# ─── TAB: Payer Perspectives ────────────────────────────────────────

with tab_payers:
    results = st.session_state.results

    if not results:
        st.info("No results yet. Run a scan with payer inference enabled.")
    else:
        # Find results that have payer perspectives
        has_perspectives = [r for r in results if r.payer_perspectives]

        if not has_perspectives:
            st.info("No payer perspectives generated. Enable 'Run payer perspective inference' and scan again.")
        else:
            payer_names = list(PAYER_INFERENCE_PROMPTS.keys())
            selected_payer = st.selectbox("Select payer perspective", payer_names)

            st.subheader(f"🧠 {selected_payer} — Inferred Strategic Perspective")

            # Show the system prompt context
            with st.expander("View payer context prompt"):
                st.code(PAYER_INFERENCE_PROMPTS[selected_payer], language="text")

            for r in has_perspectives:
                perspective = r.payer_perspectives.get(selected_payer, "")
                if not perspective or perspective.startswith("[Error"):
                    continue

                with st.expander(
                    f"{severity(r.relevance_score)} {r.article.title[:70]}"
                ):
                    st.markdown(f"**Article insight:** {r.key_insight}")
                    st.divider()
                    st.markdown(f"**{selected_payer}'s likely view:**")
                    st.markdown(perspective)
