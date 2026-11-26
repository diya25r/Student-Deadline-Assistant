import streamlit as st

from agent_core import MAX_HISTORY, run_agent


st.set_page_config(page_title="Student Deadline Assistant", page_icon="📚", layout="centered")

st.title("Student Deadline Assistant")
st.caption("Find assignment deadlines, plan your study time, and build a manageable next step.")

with st.sidebar:
    st.header("Gemini setup")
    st.markdown("Enter your own Gemini API key for this session. It is not saved by this app.")
    api_key = st.text_input("Gemini API key", type="password", placeholder="Paste your API key")
    st.caption("Get a key from Google AI Studio. Do not share it with anyone.")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for entry in st.session_state.messages:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
        if entry["role"] == "assistant":
            with st.expander("Agent Steps", expanded=False):
                if entry.get("steps"):
                    for index, step in enumerate(entry["steps"], start=1):
                        st.markdown("**{}: `{}`**".format(index, step["name"]))
                        st.code(step["arguments"], language="json")
                        st.markdown("**Result**")
                        st.write(step["result"])
                else:
                    st.caption("No tools were needed for this response.")
            if entry.get("limit_reached"):
                st.warning("The agent stopped because it reached the tool-call step limit.")

user_input = st.chat_input("Ask about an assignment or study plan")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    if not api_key.strip():
        error_message = "Add your Gemini API key in the sidebar before asking a question."
        st.session_state.messages.append({"role": "assistant", "content": error_message, "steps": []})
        with st.chat_message("assistant"):
            st.error(error_message)
    else:
        with st.chat_message("assistant"):
            with st.spinner("Checking deadlines and preparing a response..."):
                try:
                    answer, steps, limit_reached = run_agent(
                        user_input=user_input,
                        history=st.session_state.messages[:-1][-MAX_HISTORY:],
                        api_key=api_key.strip(),
                    )
                except Exception as error:
                    error_text = str(error).lower()
                    if any(term in error_text for term in ("api_key_invalid", "invalid api key", "unauthorized", "401")):
                        answer = "Gemini rejected that API key. Check that it is valid and try again."
                    else:
                        answer = (
                            "I could not complete the Gemini request. Check your API key, connection, "
                            "and available Gemini quota, then try again."
                        )
                    steps = []
                    limit_reached = False
                    st.error(answer)
                else:
                    st.markdown(answer)
                    with st.expander("Agent Steps", expanded=bool(steps)):
                        if steps:
                            for index, step in enumerate(steps, start=1):
                                st.markdown("**{}: `{}`**".format(index, step["name"]))
                                st.code(step["arguments"], language="json")
                                st.markdown("**Result**")
                                st.write(step["result"])
                        else:
                            st.caption("No tools were needed for this response.")
                    if limit_reached:
                        st.warning("The agent stopped because it reached the tool-call step limit.")

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "steps": steps,
                "limit_reached": limit_reached,
            }
        )

if not st.session_state.messages:
    st.info("Start by asking which assignments are due soon, or ask for help planning a study session.")
