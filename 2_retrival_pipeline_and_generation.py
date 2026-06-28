from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

persistent_directory="db/chroma_db"

embedding_model=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
db=Chroma(
    persist_directory=persistent_directory,
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

query="what is falcon 9"

retriever=db.as_retriever(search_kwargs={"k":3})
relevant_docs=retriever.invoke(query)

print(f"User Query {query}")
print("-----context-----")
for i,doc in enumerate(relevant_docs,1):
    print(f" Document {i} :\n{doc.page_content}\n")



combined_input = f"""
Based on the following documents, answer the user's question.

Question:
{query}

Documents:
{chr(10).join([f"- {doc.page_content}" for doc in relevant_docs])}

Instructions:
- Use only the information in the documents.
- If the answer is not present, reply:
"I don't have enough information in the provided documents."
- Do not make up facts.
"""

model = ChatGroq(model="llama-3.3-70b-versatile")

messages = [
    SystemMessage(content="you are helpful assistant."),
    HumanMessage(content=combined_input),
]

result=model.invoke(messages)
print("---------Generated Response --------")
print("content only")
print(result.content)
