import streamlit as st
from llm_pipeline import process_user_query

# ===== PAGE CONFIG =====
st.set_page_config(page_title="EDDIE", layout="wide")

# ===== SESSION STORAGE (ONLY CHAT HISTORY) =====
if "messages" not in st.session_state:
    st.session_state.messages = []   # list of {role, content}


# ===== DARK THEME UI =====
st.markdown("""
    <style>
    body {
        background-color: #0E1117;
        color: #FAFAFA;
        font-family: 'Inter', sans-serif;
    }

    .chat-bubble {
        padding: 12px 18px;
        border-radius: 12px;
        margin-bottom: 12px;
        max-width: 75%;
        line-height: 1.5;
        font-size: 16px;
        word-wrap: break-word;
    }

    .assistant {
        background-color: #1E222A;
        color: #EDEDED;
        margin-right: auto;
    }

    .user {
        background-color: #0078FF;
        color: white;
        margin-left: auto;
    }

    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #0E1117;
        padding: 15px 20px;
        border-top: 1px solid #30363D;
        z-index: 999;
    }

    .stTextInput > div > div > input {
        background-color: #1E222A;
        color: white;
        border-radius: 10px;
        padding: 12px;
        border: 1px solid #30363D;
        font-size: 16px;
    }

    .stButton > button {
        background-color: #0078FF;
        color: white;
        padding: 10px 20px;
        border-radius: 10px;
        font-size: 16px;
        border: none;
    }
    .stButton > button:hover {
        background-color: #005FCC;
    }
    </style>
""", unsafe_allow_html=True)


# ===== SIDEBAR =====
with st.sidebar:
    st.title("EDDIE ⚙️")
    if st.button("🔁 Reload"):
        st.session_state.messages = []
        st.rerun()


# ===== TITLE =====
st.markdown("<h1 style='text-align:center; color:#EDEDED;'>💼 EDDIE</h1>", unsafe_allow_html=True)
st.caption("AI Financial Research Assistant")


# ===== DISPLAY CHAT HISTORY =====
chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        bubble_class = "assistant" if msg["role"] == "assistant" else "user"
        st.markdown(
            f"<div class='chat-bubble {bubble_class}'>{msg['content']}</div>",
            unsafe_allow_html=True
        )


# ===== INPUT BAR (FIXED AT BOTTOM) =====
st.markdown("<div class='chat-input-container'>", unsafe_allow_html=True)

col1, col2 = st.columns([8, 1])
with col1:
    user_input = st.text_input("Ask EDDIE...", "", label_visibility="collapsed")

with col2:
    send = st.button("Enter")

st.markdown("</div>", unsafe_allow_html=True)


# ===== MESSAGE HANDLING =====
if send:
    if not user_input.strip():
        st.warning("⚠️ Please enter something before pressing Enter.")
    else:
        # Add user message to chat history
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        # Run LLM + dispatch logic
        final_answer = process_user_query(user_input)

        # Add assistant message to chat history
        st.session_state.messages.append({
            "role": "assistant",
            "content": final_answer
        })

        st.rerun()  # Refresh UI to show new messages
