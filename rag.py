from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage
from langchain_huggingface import ChatHuggingFace,HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from database import get_recent_messages,save_message
import os
from flask import session
import pickle
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

def load_saved_chunks(db_path):
    with open(os.path.join(db_path, "documents.pkl"), "rb") as f:
        return pickle.load(f)




load_dotenv()

embedding = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)

hybrid_retriever = None

def load_vector_db(db_path):

    global current_db
    global hybrid_retriever

    current_db = Chroma(
        persist_directory=db_path,
        embedding_function=embedding
    )

    documents = load_saved_chunks(db_path)

    bm25 = BM25Retriever.from_documents(documents)
    bm25.k = 3

    vector = current_db.as_retriever(
        search_kwargs={"k":3}
    )

    hybrid_retriever = EnsembleRetriever(
        retrievers=[vector, bm25],
        weights=[0.5, 0.5]
    )




model = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
)
def ask_question(user_question, mode="rag"):
    print(f"\nYou ask : {user_question}")

    history = []
    chat_id = session.get("chat_id")

    if not chat_id:
        raise ValueError("No active chat found.")

    rows = get_recent_messages(chat_id,10)

    for row in rows:

        if row["role"] == "user":

            history.append(
                HumanMessage(
                    content=row["content"]
                )
            )

        else:

            history.append(
                AIMessage(
                    content=row["content"]
                )
            )
   
   
    if history:

        message=[
            SystemMessage(content="Given chat history , rewrite the new question standlone and serachable . just return the rewritten question."),
            ] + history + [
            HumanMessage(content=f"new question :{user_question}")
            ]   
        
        result=model.invoke(message)
        search_question=result.content.strip()
       # print(f"Search for : {search_question}")
    else:
        search_question=user_question

    docs = hybrid_retriever.invoke(search_question)
    sources = []

    for doc in docs:
        filename = os.path.basename(doc.metadata["source"])
        sources.append(filename)

    sources = list(set(sources))

    #print(f"Found {len(docs)} relevants documents:")
    #for i,doc in enumerate(docs,1):
       # lines=doc.page_content.split('\n')[:2]
       # preview= '\n'.join(lines)
        #print(f" Doc {i} : {preview}...")
    
    mode_instruction = (
        "Use concise, direct answers that prioritize the document's stated facts."
        if mode == "rag" else
        "Use a careful step-by-step explanation when it helps, but keep every step grounded in the retrieved document context."
    )

    combined_input = f"""
    You are DocMind, a helpful AI assistant that answers questions strictly using the provided documents.

CORE RULES
- Answer only using the provided documents. Do not use outside knowledge.
- If the answer isn't found in the documents, say exactly:
  "I couldn't find that information in the uploaded documents."
- If part of an answer is stated in the documents and part is not, answer the stated part
  and explicitly say what isn't covered � never fill the gap with your own explanation
  or reasoning that isn't traceable to the text.
- Briefly note where the answer comes from (e.g. which section, table, or figure),
  but don't just repeat the source verbatim � explain it in your own words.

ANSWER LENGTH
- Default to medium length: 3�6 sentences, or a short table/list of similar size.
- Not a one-line answer, not a long report. Include the direct answer plus one layer
  of relevant context (e.g. a supporting number, comparison, or brief reason) � but stop there.
- Only go longer than this if the user explicitly asks for detail, a report, or a full explanation.

FORMATTING
- Use clean GitHub-flavored Markdown for structured answers, like ChatGPT:
  short headings when helpful, bullet lists, numbered steps, tables, blockquotes,
  inline code, and fenced code blocks when the answer type benefits from them.
- Keep simple factual answers brief, but still use Markdown when it improves readability.
- Explain / describe / tell about something ? natural paragraphs.
- List / mention / enumerate / "all items" ? bullet points.
- Compare two or more things ? a markdown table.
- Summary ? one short paragraph (3�5 sentences).
- Steps or a process ? numbered steps.
- Advantages/disadvantages ? two short labeled sections.
- Simple factual question ? 1�2 short sentences, plain text, no heading.
- Do not start every answer with a heading. Only use headings if the user explicitly
  asks for a report or document.
- Begin naturally, as if continuing a conversation � not with a title or label.

SOURCE ATTRIBUTION
- Never insert source references inline within a sentence or paragraph
  (e.g. do NOT write "...as defined in the Introduction section, AI is..." or
  "...(Unit-IV description)").
- Write the answer as clean, natural prose or formatting with no citations mixed in.
- After the full answer, add a separate line on next line starting with "Source:" followed by
  the section/page/table/figure name(s) the answer was drawn from, comma-separated
  if more than one.
- If the answer draws from multiple parts of the document, list all of them on that
  single Source line � don't repeat citations after every sentence.

REASONING
- You may explain *how* you arrived at an answer using facts from the documents
  (e.g. combining a table value with a stated cause).
- You may NOT invent causal mechanisms, explanations, or elaborations that are not
  stated in or directly computable from the documents, even if they sound plausible.
  If you're inferring something beyond a literal computation, flag it clearly as an
  inference rather than presenting it as fact from the source.

RESPONSE MODE
- {mode_instruction}
    Question:
    {user_question}

    Retrieved Context:
        {'\n\n'.join(doc.page_content for doc in docs)}
    """
       
    messages = [
    SystemMessage(
        content="You are DocMind, a helpful assistant that answers questions and generates all responses based on the provided documents and conversation history."
    )
    ] + history + [
        HumanMessage(content=combined_input)
    ]

    result = model.invoke(messages)
    answer = result.content

    save_message(
    session["chat_id"],
    "user",
    user_question
    )

    save_message(
        session["chat_id"],
        "assistant",
        answer
    )

    
    print("\nAnswer:")
    print(answer)

    return {
    "answer": answer,
    "sources": sources
    }





def start_chat():
    print("Ask Me questions! type 'quit' to exit.")

    while True:
        question=input("\nYour Question : ")
        if question.lower()=='quit':
            print("GoodBye.")
            break
        
        ask_question(question)

if __name__=="__main__":
    start_chat()
