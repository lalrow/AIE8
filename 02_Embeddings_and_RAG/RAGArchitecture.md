

```mermaid
flowchart LR
    subgraph Ingestion[Document Ingestion Pipeline]
        A[Step 1: Source Documents<br/>(txt, pdf, html)]
        B[Step 2: Chunking / Split]
        C[Step 3: Embeddings]
        D[(Step 4: Vector Database)]
        
        A --> B --> C --> D
    end

    subgraph Query[User Query Flow]
        U([👤 Step 5: User Query])
        Q[Step 6: Query Embedding]
        R[Step 7: Similarity Search]
        CT[Step 8: Context Retrieval<br/>(Top K chunks)]
        L[Step 9: LLM Generate Answer]
        
        U --> Q --> R
        R --> D
        D --> R
        R --> CT
        CT --> L
    end
