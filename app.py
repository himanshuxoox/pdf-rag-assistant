import os
import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000"

# To this:
#API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")

# Must be the first Streamlit command
st.set_page_config(
    page_title="AI Document Assistant", 
    page_icon="✨", 
    layout="wide",
    initial_sidebar_state="expanded" # <--- Add this!
)

# ==========================================
# CUSTOM CSS STYLING
# ==========================================
st.markdown("""
<style>
    /* Add top padding and hide the default Streamlit header */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
     /* header {visibility: hidden;}*/
    footer {visibility: hidden;}
    
    /* Make buttons slightly rounded */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        width: 100%;
    }
    
    /* Style the chat input box */
    .stChatInputContainer {
        padding-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# SIDEBAR: CONTROLS & UPLOAD
# ==========================================
with st.sidebar:
    st.title("✨ AI Assistant")
    st.caption("Your personal document brain.")
    st.divider()

    st.subheader("📁 Upload Document")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", label_visibility="collapsed")
    
    if st.button("🚀 Upload & Process", type="primary") and uploaded_file is not None:
        with st.status("Processing Document...", expanded=True) as status:
            st.write("📤 Sending to server...")
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            response = requests.post(f"{API_URL}/upload", files=files)
            
            if response.status_code == 200:
                doc_id = response.json()["document_id"]
                st.session_state["current_doc_id"] = doc_id
                
                st.write("🧠 AI is analyzing and vectorizing...")
                while True:
                    status_res = requests.get(f"{API_URL}/document/{doc_id}")
                    if status_res.status_code == 200:
                        doc_data = status_res.json()
                        if doc_data["status"] == "completed":
                            st.session_state["summary"] = doc_data["summary"]
                            st.session_state["filename"] = doc_data["filename"]
                            # Clear chat history when new doc is uploaded
                            st.session_state.messages = [] 
                            status.update(label="Ready!", state="complete", expanded=False)
                            break
                        elif "failed" in doc_data["status"]:
                            status.update(label="Error processing", state="error")
                            st.error(doc_data['status'])
                            break
                    time.sleep(1.5)
                time.sleep(1)
                st.rerun()
            else:
                status.update(label="Upload failed", state="error")

    st.divider()

    # Search section moved to sidebar
    st.subheader("🔍 Search Database")
    search_query = st.text_input("Find topics across all PDFs:", placeholder="e.g. 'Revenue growth'")
    if st.button("Search Vectors") and search_query:
        with st.spinner("Searching..."):
            res = requests.post(f"{API_URL}/search", json={"query": search_query, "limit": 2})
            if res.status_code == 200:
                results = res.json()["results"]
                if not results:
                    st.info("No relevant matches found.")
                for r in results:
                    with st.expander(f"📄 {r['filename']}", expanded=False):
                        st.write(r['summary'][:150] + "...")


# ==========================================
# MAIN SCREEN: CHAT & READING
# ==========================================
if "current_doc_id" in st.session_state:
    
    # Header showing active document
    st.subheader(f"📖 Active Document: `{st.session_state.get('filename', 'Unknown')}`")
    
    # Beautifully styled expander for the summary
    with st.expander("💡 View AI Executive Summary", expanded=False):
        st.info(st.session_state.get("summary", "No summary available."))
        
    st.divider()
    
    # Chat Interface
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display previous chat messages with custom avatars
    for message in st.session_state.messages:
        avatar = "🧑‍💻" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Chat Input box
    if prompt := st.chat_input("Ask a question about this PDF..."):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                chat_payload = {
                    "document_id": st.session_state["current_doc_id"],
                    "message": prompt
                }
                chat_res = requests.post(f"{API_URL}/chat", json=chat_payload)
                
                if chat_res.status_code == 200:
                    ai_response = chat_res.json()["response"]
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                else:
                    st.error("Error communicating with AI backend.")


else:
    # Empty State UI
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    colA, colB, colC = st.columns([1, 2, 1])
    with colB:
        st.markdown("<h1 style='text-align: center; color: #6366f1;'>✨ AI Document Brain</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 18px; color: gray;'>Upload a PDF in the sidebar to extract text, generate a summary, and begin chatting instantly.</p>", unsafe_allow_html=True)
        st.info("👈 Open the sidebar to upload your first document.")