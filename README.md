# 🎓 NSRIT Exam Cell AI Assistant ("Cella")

[![Frontend Deployment](https://img.shields.io/badge/Frontend-Render-success?style=for-the-badge&logo=render)](https://examcell-chatbot-1.onrender.com)
[![Backend Deployment](https://img.shields.io/badge/Backend-Railway-blueviolet?style=for-the-badge&logo=railway)](https://examcell-chatbot-production.up.railway.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Groq AI](https://img.shields.io/badge/Groq_API-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)

> An intelligent, autonomous **Retrieval-Augmented Generation (RAG)** chatbot and document management portal for the **Nadimpalli Satyanarayana Raju Institute of Technology (NSRIT)** Examination Cell.

---

## 🌟 Live Demo

* **🌐 Frontend Web Application**: [https://examcell-chatbot-1.onrender.com](https://examcell-chatbot-1.onrender.com)
* **⚡ Backend API (FastAPI)**: [https://examcell-chatbot-production.up.railway.app](https://examcell-chatbot-production.up.railway.app)
* **📑 Interactive API Swagger Docs**: [https://examcell-chatbot-production.up.railway.app/docs](https://examcell-chatbot-production.up.railway.app/docs)

---

## 📸 Key Features

### 🤖 1. AI Exam Cell Assistant ("Cella")
* **Retrieval-Augmented Generation (RAG)**: Answers student questions using verified college documents as ground truth without hallucinations.
* **Instant Answers**: Sem timetables, mid examination schedules, supply fees, revaluation dates, and official notices.
* **Citation & Document Downloads**: Directly provides snippet citations and one-click download links for original PDF/DOCX circulars.
* **Conversational Context**: Retains conversational history for intuitive follow-up inquiries.

### 📄 2. Intelligent Document Processing & OCR
* **Multi-Format Extraction**: Parses tables and multi-column circulars from both PDF (`pdfplumber`, `PyMuPDF`) and Word (`python-docx`).
* **Computer Vision & OCR**: Fallback OCR pipeline via `pytesseract` and `opencv-python-headless` for scanned, photocopied, or degraded circulars.
* **Automated Chunking & Metadata Tagging**: Detects academic year, regulation (AR20, AR20 Rev 1.0, AR23), semester, and exam types.

### 🔍 3. Hybrid Semantic & Lexical Search
* **Semantic Embeddings**: Powered by `sentence-transformers` (`all-MiniLM-L6-v2`) with PyTorch CPU optimization.
* **High-Speed Vector Storage**: Lightweight SQLite vector store and ChromaDB fallback.
* **Lexical Re-Ranking**: Boosts keyword exact matches (exam type, semester, regulations, admitted batches) for high precision.

### 🔐 4. Admin Management Portal
* **Staff Login**: Secure authentication for exam cell coordinators.
* **Live Knowledge Base Metrics**: Real-time counter of ingested documents and vector chunks.
* **Batch Ingestion & Reset**: Upload new notifications on the fly or reset database indexes.

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    A[Student / User] -->|Queries UI| B[React + Vite Frontend (Render)]
    B -->|REST API Requests| C[FastAPI Server (Railway)]
    C -->|Vector Similarity Query| D[(SQLite Vector Store & ChromaDB)]
    C -->|Top Matching Context| E[Groq LLM Engine]
    E -->|Structured Accurate Response| C
    C -->|JSON Payload + Citations| B
    F[Exam Cell Admin] -->|Uploads Circulars| C
    C -->|Extract & OCR| G[PDFPlumber / Tesseract]
    G -->|Text Chunker| H[all-MiniLM-L6-v2 Embeddings]
    H -->|Persist Embeddings| D
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite | Fast, responsive Single-Page Application (SPA) |
| **Styling & UI** | Tailwind CSS, Lucide Icons, Framer Motion | Clean, modern interface with micro-interactions |
| **Backend API** | FastAPI, Uvicorn, Pydantic | High-performance asynchronous REST API |
| **LLM Inference** | Groq Cloud API | High-speed LLM response generation |
| **Embeddings** | `sentence-transformers` (`all-MiniLM-L6-v2`) | Dense semantic vector representations |
| **Document Processing** | `PyMuPDF`, `pdfplumber`, `python-docx` | Native PDF & Word document parsing |
| **OCR & Vision** | `pytesseract`, `Pillow`, `OpenCV` | Image preprocessing and text recognition |
| **Database** | SQLite3, ChromaDB | Persistent vector storage and document indexing |
| **Deployment** | Render (Frontend) & Railway (Backend) | Production cloud hosting |

---

## 📂 Repository Structure

```
CAPSTONE/
├── backend/
│   ├── backend/
│   │   ├── ingestion/
│   │   │   ├── chunker.py           # Text segmentation & overlap logic
│   │   │   ├── extract.py           # PDF/DOCX parsing & metadata tagging
│   │   │   └── ocr.py               # Tesseract OCR & image enhancement
│   │   ├── llm/
│   │   │   └── groq_llm.py          # Groq client integration & RAG prompt
│   │   └── retrieval/
│   │       └── search.py            # Hybrid semantic + lexical retrieval engine
│   ├── documents/
│   │   └── original/                # Ingested PDF and DOCX examination circulars
│   ├── knowledge_base/
│   │   ├── db.sqlite3               # Vector storage & chunk embeddings
│   │   ├── chunks.json              # Document chunks cache
│   │   └── documents.json           # Document metadata catalogue
│   ├── chat_api.py                  # Main FastAPI application & endpoints
│   └── .env                         # Environment variables (Groq API Key)
├── frontend/
│   ├── src/
│   │   ├── components/              # Chatbot popup, Navbar, Footer, UI components
│   │   ├── pages/                   # Home, Dashboard, Examcell Login
│   │   └── lib/                     # Utilities and helpers
│   ├── package.json                 # Node dependencies
│   └── vite.config.ts               # Vite configuration
├── Procfile                         # Cloud process definition for Railway
├── railway.json                     # Railway deployment configuration
├── requirements.txt                 # Optimized Python backend dependencies
└── README.md                        # Documentation
```

---

## 🚀 Local Development Setup

### Prerequisites
* **Python**: `3.11`
* **Node.js**: `v18+` or `v20+`
* **Git**
* **Groq API Key**: (Get one free at [console.groq.com](https://console.groq.com/))

---

### 1. Backend Setup

```powershell
# 1. Navigate to backend directory
cd backend

# 2. Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows
# source venv/bin/activate    # On Linux/macOS

# 3. Install dependencies
python -m pip install -r ..\requirements.txt

# 4. Configure environment variables
# Create a .env file inside backend/ directory:
echo "GROQ_API_KEY=your_actual_groq_api_key_here" > .env

# 5. Start the backend server
python -m uvicorn chat_api:app --reload
```
The backend will start at: `http://localhost:8000`  
Check health status: `http://localhost:8000/health`

---

### 2. Frontend Setup

Open a second terminal:

```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```
The frontend will start at: `http://localhost:8080` (or `http://localhost:5173`)

---

## 🔒 Admin Credentials (Demo)

* **URL**: `/examcell-login`
* **Email**: `examcell@nsrit.edu.in`
* **Password**: `examcell@nsrit`

---

## ☁️ Deployment Guide

### Deploy Backend (Railway)
1. Fork or clone this repository to GitHub.
2. In [Railway](https://railway.com/), create a **New Project** ➡️ **Deploy from GitHub repo**.
3. Under **Variables**, add:
   * `GROQ_API_KEY` = `your_groq_api_key`
4. Under **Settings ➡️ Networking**, click **Generate Domain**.

### Deploy Frontend (Render)
1. In [Render](https://dashboard.render.com/), create a **New Static Site**.
2. Connect your GitHub repository.
3. Settings:
   * **Root Directory**: `frontend`
   * **Build Command**: `npm install && npm run build`
   * **Publish Directory**: `dist`
4. Environment Variables:
   * `VITE_API_BASE` = `https://your-backend.up.railway.app`

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 👨‍💻 Author

**Tungana Vinod Kumar**
* GitHub: [@TunganaVinodKumar](https://github.com/TunganaVinodKumar)
* Project Repo: [examcell-chatbot](https://github.com/TunganaVinodKumar/examcell-chatbot)
* College: Nadimpalli Satyanarayana Raju Institute of Technology (NSRIT)
