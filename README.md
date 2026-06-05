# PDF RAG Assistant 📄🤖

A full-stack AI Document Assistant built to perform local embedding generation, semantic search, and Retrieval-Augmented Generation (RAG) on PDF documents. 

## 🚀 Overview
PDF RAG Assistant is designed to help you interactively query and extract insights from your PDF files. It leverages a modern Python stack with an interactive UI, a fast API backend, and an advanced vector database setup for accurate and efficient semantic search.

## ✨ Features
* **PDF Processing:** Easily upload and parse PDF documents.
* **Local Embedding Generation:** Generate text embeddings locally without relying on external APIs for data privacy.
* **Semantic Search:** Quickly retrieve relevant chunks of information from your documents.
* **Retrieval-Augmented Generation (RAG):** Get accurate, context-aware answers to your questions based strictly on the uploaded document contents.

## 🛠️ Tech Stack
* **Frontend:** [Streamlit](https://streamlit.io/) (`app.py`)
* **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (`main.py`)
* **Database & Vector Store:** PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension
* **Language:** Python 100%

## 📂 Repository Structure
* `app.py` - The Streamlit application for the user interface.
* `main.py` - The FastAPI application serving the backend logic and API endpoints.
* `requirements.txt` - Project dependencies.
* `.streamlit/` - Streamlit configuration files.
* `.gitignore` - Standard git ignore definitions.

## ⚙️ Getting Started

### Prerequisites
* Python 3.8+
* PostgreSQL installed and running
* The `pgvector` extension enabled on your PostgreSQL database

### Installation & Setup
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/himanshuxoox/pdf-rag-assistant.git](https://github.com/himanshuxoox/pdf-rag-assistant.git)
   cd pdf-rag-assistant
