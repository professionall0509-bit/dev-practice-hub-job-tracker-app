import os
import chromadb
from pypdf import PdfReader

class ResumeRAG:
    def __init__(self, chroma_path="./chroma_db"):
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(name="resume_chunks")

    def index_resume(self, pdf_path="resume.pdf"):
        if not os.path.exists(pdf_path):
            return "Resume PDF not found."

        reader = PdfReader(pdf_path)
        chunks = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                # Basic chunking by paragraph
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                for j, para in enumerate(paragraphs):
                    chunks.append({
                        "id": f"page_{i}_chunk_{j}",
                        "text": para
                    })

        if chunks:
            self.collection.upsert(
                documents=[c["text"] for c in chunks],
                ids=[c["id"] for c in chunks]
            )
        return f"Successfully indexed {len(chunks)} resume sections into ChromaDB."

    def query_resume(self, query_text, n_results=3):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        if results and results["documents"]:
            return "\n---\n".join(results["documents"][0])
        return "No relevant resume context found."
