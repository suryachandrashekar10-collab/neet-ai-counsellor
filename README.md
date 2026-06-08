# NEET AI Counsellor

AI-powered platform democratizing medical college admissions guidance for Maharashtra NEET aspirants.

## What it does
- Extracts student profile from NEET scorecard via OCR
- Compares rank against 5 years of Maharashtra MCC counselling data
- Predicts admission probability per college per round
- Generates optimized preference lists (reach / target / safe)
- AI chat counsellor for follow-up questions
- Pre-fills MCC application forms

## Project Structure
```
data/           # raw PDFs, parsed CSVs, embeddings
backend/        # FastAPI + probability engine
frontend/       # Next.js dashboard
rag/            # Qdrant vector store + retrieval pipeline
notebooks/      # data exploration, model backtesting
```

## Tech Stack
- **Frontend**: Next.js 14, React, Tailwind CSS
- **Backend**: Python 3.11, FastAPI
- **AI**: Claude / GPT-4o, LangGraph
- **RAG**: Qdrant, text-embedding-3-large
- **Data**: PostgreSQL 16, Redis
- **OCR**: pdfplumber, Tesseract

## MVP Roadmap
- Month 1: Data collection and parsing pipeline
- Month 2: RAG + recommendation engine
- Month 3: Frontend + AI assistant
- Month 4: Beta launch
