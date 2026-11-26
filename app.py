"""Streamlit interface for the Student Deadline Assistant capstone."""

import streamlit as st

from graph_core import MAX_HISTORY, run_graph
from rag_core import build_vector_store

SUGGESTED_QUESTIONS = [
    "How can I break a large assignment into smaller tasks?",
    "What study techniques help with remembering concepts?",
    "How should I plan my week before a deadline?",
    "Create a study plan for 10 hours of work across 5 days.",
]

st.set_page_config(
    page_title="Student Deadline Assistant",
    page_icon="📚",
    layout="centered",
)


def _clear_vector_store() -> None:
    st.session_state.pop("vector_store", None)


def _show_assistant_message(entry: dict) -> None:
    st.markdown(entry["content"])
    route = entry.get("route", "not run")
    path = entry.get("execution_path", [])
    path_text = " → ".join(path) if path else "not available"
    st.caption("Route: {}  |  Graph path: {}".format(route, path_text))

    if route == "docs":
        with st.expander("Sources", expanded=False):
            sources = entry.get("sources", [])
            if not sources:
                st.caption("No supporting passages were retrieved.")
            for source in sources:
                page = source.get("page")
                page_label = "page {}".format(page) if page is not None else "page not available"
                st.markdown("**{} — {}**".format(source.get("source", "Unknown source"), page_label))
                st.write(source.get("content", ""))
    elif route == "tools":
        with st.expander("Agent Steps", expanded=bool(entry.get("steps"))):
            steps = entry.get("steps", [])
            if not steps:
                st.caption("The agent did not need to call a tool.")
            for index, step in enumerate(steps, start=1):
                st.markdown("**{}. `{}`**".format(index, step["name"]))
                st.code(step["arguments"], language="json")
                st.markdown("**Tool result**")
                st.write(step["result"])

    if entry.get("limit_reached"):
        st.warning("The graph stopped because it reached its step limit.")


if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Student Deadline Assistant")
st.caption(
    "Get grounded study guidance, calculate a manageable study pace, and draft an assignment plan."
)

with st.sidebar:
    st.header("Your Gemini API key")
    st.markdown("Paste a personal key for this session. The app does not write it to a file.")
    api_key = st.text_input(
        "Gemini API key",
        type="password",
        placeholder="Paste your Gemini API key",
        on_change=_clear_vector_store,
    )
    st.caption("Create a key in Google AI Studio. Never share it or commit it to GitHub.")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

for entry in st.session_state.messages:
    with st.chat_message(entry["role"]):
        if entry["role"] == "assistant":
            _show_assistant_message(entry)
        else:
            st.markdown(entry["content"])

st.subheader("Suggested Questions")
suggested_question = None
question_columns = st.columns(2)
for index, suggestion in enumerate(SUGGESTED_QUESTIONS):
    with question_columns[index % 2]:
        if st.button(suggestion, key="suggested_question_{}".format(index), use_container_width=True):
            suggested_question = suggestion

typed_question = st.chat_input("Ask a study, assignment, or deadline question")
user_question = suggested_question or typed_question

if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    if not api_key.strip():
        response = {
            "answer": "Enter your Gemini API key in the sidebar before starting a chat.",
            "route": "not run",
            "execution_path": [],
            "sources": [],
            "steps": [],
            "limit_reached": False,
        }
        with st.chat_message("assistant"):
            st.error(response["answer"])
    else:
        try:
            if "vector_store" not in st.session_state:
                with st.spinner("Loading and indexing the study documents..."):
                    st.session_state.vector_store = build_vector_store(api_key.strip())
            with st.chat_message("assistant"):
                with st.spinner("Thinking through your question..."):
                    response = run_graph(
                        user_input=user_question,
                        history=st.session_state.messages[:-1][-MAX_HISTORY:],
                        api_key=api_key.strip(),
                        vector_store=st.session_state.vector_store,
                    )
                _show_assistant_message(
                    {
                        "role": "assistant",
                        "content": response["answer"],
                        **response,
                    }
                )
        except Exception as error:
            error_text = str(error).casefold()
            if any(
                marker in error_text
                for marker in ("api_key_invalid", "invalid api key", "unauthorized", "401")
            ):
                message = "Gemini rejected that key. Check that it is valid, then try again."
            elif "knowledge_base" in error_text or "knowledge-base" in error_text:
                message = (
                    "The study documents could not be loaded. Check that the knowledge_base "
                    "folder contains readable .txt, .md, or text-based .pdf files."
                )
            else:
                message = (
                    "I could not complete the request. Check your Gemini key, network connection, "
                    "available API quota, and study documents, then try again."
                )
            response = {
                "answer": message,
                "route": "not run",
                "execution_path": [],
                "sources": [],
                "steps": [],
                "limit_reached": False,
            }
            with st.chat_message("assistant"):
                st.error(message)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response["answer"],
            "route": response["route"],
            "execution_path": response["execution_path"],
            "sources": response["sources"],
            "steps": response["steps"],
            "limit_reached": response["limit_reached"],
        }
    )

if not st.session_state.messages:
    st.info("Choose a suggested question or type your own to get started.")
