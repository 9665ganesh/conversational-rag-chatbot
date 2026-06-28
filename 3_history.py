from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage
from langchain_huggingface import ChatHuggingFace,HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

persistent_directory="db/chroma_db"
embedding=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
db=Chroma(
    persist_directory=persistent_directory,
    embedding_function=embedding,
)
model = ChatGroq(model="llama-3.3-70b-versatile")

chat_history=[]

def ask_question(user_question):
    print(f"\nYou ask : {user_question}")

    if chat_history:

        message=[
            SystemMessage(content="Give chat history , rewrite the new question standlone and serachable . just return the rewritten question."),
            ] + chat_history + [
            HumanMessage(content=f"new question :{user_question}")
            ]   
        
        result=model.invoke(message)
        search_question=result.content.strip()
        print(f"Search for : {search_question}")
    else:
        search_question=user_question

    retriever=db.as_retriever(search_kwargs={"k":3})
    docs=retriever.invoke(search_question)

    #print(f"Found {len(docs)} relevants documents:")
    #for i,doc in enumerate(docs,1):
       # lines=doc.page_content.split('\n')[:2]
       # preview= '\n'.join(lines)
        #print(f" Doc {i} : {preview}...")
    
    combined_input=f''' Based on the following documents,Please answer this question :{user_question}
    documents:
    {'\n'.join([f"-{doc.page_content}" for doc in docs])}
    Instructions:
    - Use only the information in the documents.
    - If the answer is not present, reply:
    "I don't have enough information in the provided documents."
    - Do not make up facts.
    '''

    messages = [
    SystemMessage(
        content="You are a helpful assistant that answers questions based on the provided documents and conversation history."
    )
    ] + chat_history + [
        HumanMessage(content=combined_input)
    ]

    result = model.invoke(messages)
    answer = result.content

    chat_history.append(HumanMessage(content=user_question))
    chat_history.append(AIMessage(content=answer))

    print("\nAnswer:")
    print(answer)

    return answer

def start_chat():
    print("Ask Me questions! type 'quit' to exit.")

    while True:
        question=input("\nYour Question:")
        if question.lower()=='quit':
            print("GoodBye.")
            break
        
        ask_question(question)

if __name__=="__main__":
    start_chat()
    
