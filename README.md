# PDF Q&A System over the Microsoft 2025 Annual Report

## Overview

This project is a local Retrieval-Augmented Generation (RAG) system built over the **Microsoft 2025 Annual Report**. It accepts a natural-language question, retrieves relevant passages from the PDF, and returns a grounded answer with source references.

The system was designed to satisfy the assignment requirements:

- `POST /ask` endpoint using FastAPI
- ingestion pipeline for extraction, chunking, embedding, and storage
- vector store choice documented
- honest evaluation with both working and failing cases
- README covering chunking, limitations, and improvement paths

## Why this PDF

I chose the **Microsoft 2025 Annual Report** because it is:

- publicly available
- machine-readable
- well structured with headings and sections
- rich in both narrative and financial content

That makes it a good test document for a PDF Q&A system because it supports:
- easy factual questions
- numeric questions
- strategic/business questions
- questions that reveal realistic retrieval failures

## Tech Stack

- **API**: FastAPI
- **Vector DB**: Chroma (persistent local)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **LLM answering**: OpenAI API (`gpt-4o-mini` by default)
- **PDF extraction**: PyMuPDF
- **Language**: Python

## Project Structure

```text
rag_chatbot/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── schemas.py
│   └── services/
│       ├── __init__.py
│       ├── answer_service.py
│       ├── chroma_service.py
│       ├── prompt_builder.py
│       └── retriever.py
├── data/
│   ├── raw/
│   │   ├── microsoft_2025_annual_report.pdf
│   │   └── document_manifest.json
│   ├── processed/
│   │   ├── extracted_pages.json
│   │   ├── chunks.jsonl
│   │   └── eval_results.json
│   └── chroma_db/
├── eval/
│   └── questions.json
└── scripts/
    ├── extract_pdf.py
    ├── build_chunks.py
    ├── ingest.py
    ├── run_eval.py
    ├── test_answering.py
    └── test_retrieval.py
```

## Pipeline

### 1) PDF extraction
The report is parsed page by page using **PyMuPDF**. The extractor writes a structured JSON file with:

- page number
- raw extracted text
- cleaned text
- character count
- whether the page has text

### 2) Text cleaning
The cleaning layer removes obvious extraction noise while preserving meaning:

- normalized whitespace
- removed standalone page numbers
- removed artifact lines like `**`
- fixed hyphenated line breaks such as `low-\nvision`

### 3) Chunking
The document is chunked using a **section-aware, paragraph-based** strategy.

Each chunk stores:
- `chunk_id`
- `page_start`
- `page_end`
- `section`
- `text`
- `word_count`

Important chunking rules:
- all-caps headings are treated as section markers
- heading-only chunks are suppressed
- overlap is retained across chunk boundaries
- `page_start` and `page_end` are tracked for source attribution

### 4) Embedding and storage
Chunks are embedded with `all-MiniLM-L6-v2` and stored in a **persistent local Chroma collection**.

Collection name:
- `msft_annual_report_2025`

Stored metadata:
- `chunk_id`
- `page_start`
- `page_end`
- `section`
- `word_count`
- `document_id`

### 5) Retrieval
Retrieval is a **two-stage** process:

1. dense retrieval from Chroma
2. lightweight lexical reranking over the top dense items

This was necessary because dense retrieval alone returned semantically similar but incorrect chunks for some exact strategic questions.

### 6) Answer generation
The answering step sends the retrieved chunks to an LLM with a grounded prompt that instructs it to:

- answer only from the provided context
- avoid inventing facts
- say when the context is insufficient
- keep the answer concise

### 7) API
The FastAPI app exposes:

- `GET /health`
- `POST /ask`

Example request:

```json
{
  "question": "Is Microsoft profitable?"
}
```

Example response:

```json
{
  "answer": "Yes. Microsoft was profitable in fiscal year 2025...",
  "sources": [
    {
      "chunk_id": "chunk_0051",
      "page_start": 24,
      "page_end": 25,
      "section": "SUMMARY RESULTS OF OPERATIONS"
    }
  ]
}
```

## Why Chroma

I chose **Chroma** because this project is:
- local
- small
- single-document
- metadata-driven

For this use case, Chroma gave the easiest local persistent vector store setup. It stores embeddings, chunk text, and metadata in one place, which made development faster than using a lower-level library such as FAISS.

### Why not FAISS
FAISS would have worked, but I would have needed to manage metadata and persistence more manually.

### Why not Qdrant
Qdrant would be a stronger production-style choice, but it adds more infrastructure overhead for a small local project.

### Why not pgvector
pgvector is attractive when the app already uses Postgres. This project did not need a relational database for its first version.

## Index type / distance choice

The vector store is a persistent local Chroma collection. On single-node Chroma, vector search uses an HNSW-based approximate nearest-neighbor index, and this project configures the collection with cosine distance via `metadata={"hnsw:space": "cosine"}`. That combination was chosen because the embedding model, `all-MiniLM-L6-v2`, is a text embedding model, and cosine similarity is the more natural fit for comparing text embeddings than leaving the collection on the default distance setting. 

### Why this vector store

I chose **Chroma** because this is a **small, local, single-document** RAG system and I wanted the simplest persistent setup that could store **documents, embeddings, and metadata together**. For this scale of project, Chroma reduced infrastructure overhead compared with running a separate vector database service, while still keeping the retrieval layer realistic enough for a production-style RAG prototype.

### Why this index type

I kept Chroma’s built-in **HNSW** approach rather than introducing a different vector backend because the corpus is small and the main goal was a simple, inspectable local system. HNSW is appropriate here because it gives fast approximate nearest-neighbor retrieval without forcing me to manage a lower-level index manually. Given the project size, the more important decision was not replacing the index structure, but choosing the correct **distance metric** and then improving ranking with a lightweight lexical reranker. 

### Why cosine distance

I initially found that dense retrieval alone was returning semantically similar but incorrect chunks for some strategic questions. Configuring the collection for **cosine distance** was the right baseline because the embeddings were normalized text embeddings. This improved the retrieval setup, although it did **not** fully solve ranking for exact strategy-oriented queries, which is why I later added a lexical reranking layer on top of dense retrieval. 

## Latency: cold vs warm

In this project, **cold retrieval** means the first retrieval calls after startup, when the retriever, embedding model, and local Chroma collection have just been initialized. **Warm retrieval** means later retrievals after those components are already loaded and reusable in memory. Because this is a small local corpus, retrieval itself is relatively cheap; the answer-generation step is the slower part of the full question-answering path. 

### Measured retrieval timings

From the benchmark file:

- **Cold retrieval**: 3 runs, min **21.01 ms**, max **91.27 ms**, mean **47.33 ms**, p50 **29.70 ms**, p95 **29.70 ms**. 
- **Warm retrieval**: 30 runs, min **15.26 ms**, max **166.99 ms**, mean **33.83 ms**, p50 **30.98 ms**, p95 **38.34 ms**. 

These numbers show that retrieval itself is already fairly fast on this dataset. Warm retrieval is typically around **31 ms median**, which is consistent with a small, local single-document vector search pipeline. The occasional slower warm outlier pushes the max to **166.99 ms**, but the p95 of **38.34 ms** shows that most warm retrievals stayed well below that. 

### Measured full answer timings

From the same benchmark file:

- **Cold full answer**: 3 runs, min **1346.73 ms**, max **3700.93 ms**, mean **2205.68 ms**, p50 **1569.38 ms**, p95 **1569.38 ms**. 
- **Warm full answer**: 30 runs, min **1159.46 ms**, max **3303.66 ms**, mean **1898.01 ms**, p50 **1720.14 ms**, p95 **2806.00 ms**. 

This shows that the main latency cost in the end-to-end system is **LLM answer generation**, not vector retrieval. Retrieval is measured in **tens of milliseconds**, while the full answer path is measured in roughly **1.2 to 3.3 seconds** depending on run conditions.

### How I would improve latency

The first optimization is **startup reuse**: load the embedding model once, keep the Chroma client open, and reuse the retriever and answer service across requests. The second is **candidate reduction**: keep `initial_k` modest and pass only the strongest chunks to the answer model. The third is **caching**: cache repeated question embeddings and optionally cache full answers for repeated questions. The fourth is **asynchronous answer generation** or better request concurrency handling, because the LLM call is the clear bottleneck. Finally, I would only tune the vector index further if retrieval latency or recall became a real bottleneck, because the current measurements show retrieval is already cheap relative to generation.

## Setup

## 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

## 2. Install dependencies

```bash
pip install fastapi uvicorn chromadb sentence-transformers pymupdf openai python-dotenv
```

## 3. Add environment variables

Create a `.env` or export variables:

```bash
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
```

## 4. Place the PDF

Put the source file at:
note:I have not included the file here as it would increase the size of this project unnecessarily,
but you can download it from internet

```text
data/raw/2025_AnnualReport.pdf
```

## Run order

### Step 1: extract text

```bash
python scripts/extract_pdf.py
```

### Step 2: build chunks

```bash
python scripts/build_chunks.py
```

### Step 3: ingest into Chroma

```bash
python scripts/ingest.py
```

### Step 4: test retrieval manually

```bash
python scripts/test_retrieval.py "Is Microsoft profitable?" --k 5
```

### Step 5.1: test retrieval + answer generation

```bash
python scripts/test_answering.py "Is Microsoft profitable?"
```


### Step 5.2: Record Benchmark Timings

```bash
python scripts/benchmark_retrieval.py --include-answer
```

### Step 6: run the API

```bash
uvicorn app.main:app --reload
```

### Step 7: test the API

PowerShell example:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/ask" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"Is Microsoft profitable?"}'
```

## Honest evaluation

The assignment explicitly asks for an honest evaluation. This system does **not** work perfectly, and the failures are informative.

### Example of a working query
**Question:** Is Microsoft profitable?

This typically retrieves strong evidence from the financial results section and produces a correct grounded answer citing revenue, operating income, and net income.

### Example of a difficult / failing query
**Question:** What were Microsoft’s three core business priorities?

This is a known harder case. The answer exists in the document, but retrieval may rank semantically similar business or financial chunks above the actual `OUR PRIORITIES` section. Dense retrieval alone performed poorly here, and even lexical reranking only improved it partially.

## Evaluation question set

The `eval/questions.json` file includes a mix of:
- easy factual questions
- numeric questions
- strategic questions
- sustainability questions
- one likely unanswerable question

Examples:
- Is Microsoft profitable?
- What was Microsoft’s revenue in fiscal year 2025?
- What is Microsoft Elevate?
- How many LinkedIn members did Microsoft report?
- What remained in the share repurchase program as of June 30, 2025?
- What exact AI policy did Microsoft announce for all governments in Asia?

## What breaks

### 1) Dense retrieval on exact strategic phrasing
Semantic retrieval sometimes surfaces broad business-related chunks instead of the exact strategy section.

### 2) Flattened tables
Financial tables are extracted as linear text, which makes row/column reasoning weaker.

### 3) Heading detection is still imperfect
Some headings that are not strong all-caps markers may remain inside chunks instead of becoming new chunk boundaries.

### 4) Weak source filtering
The answer layer currently returns all retrieved sources, including some weakly relevant ones. This can be tightened later.

## What I would fix first

### First improvement: stronger hybrid retrieval
Add a proper lexical BM25-style component or stronger reranker so exact phrases like “core business priorities” are handled better.

### Second improvement: table-aware handling
Treat financial tables separately instead of chunking them exactly like narrative text.

### Third improvement: source filtering
Return only the most relevant 2–3 sources instead of every retrieved chunk passed to the answerer.



## Summary

This project successfully demonstrates a local PDF Q&A pipeline over a real annual report with:
- extraction
- chunking
- embeddings
- local vector storage
- retrieval
- grounded answer generation
- API delivery

Its biggest lesson is that **retrieval quality matters more than the API layer**, especially for structured business documents where exact phrasing and financial tables matter.
