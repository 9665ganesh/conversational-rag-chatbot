import os
from langchain_community.document_loaders import TextLoader , DirectoryLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv




def load_documents(docs_path="docs"):
    '''loading all text file from docs directory...'''
    print(f"loading documents from {docs_path}")


    

    if not os.path.exists(docs_path):
        raise FileNotFoundError(f"the directory {docs_path} is not exist...")
    
    loader = DirectoryLoader(
        path=docs_path,
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={
            "encoding": "utf-8"
        }
    )

    documents=loader.load()
    if len(documents)==0:
        raise FileNotFoundError(f"No txt file found in {docs_path}")
    

    for i,doc in enumerate(documents[:2]):
        print(f"\nDocument {i+1}")
        print(f" Source: {doc.metadata['source']}")
        print(f" Content Length: {len(doc.page_content)} characater")
        print(f" Content Preview: {doc.page_content[:100]}")
        print(f" Metadata : {doc.metadata} ")

    return documents
    

def split_documents(documents , chunk_size=800,chunk_overlap=0):
    '''Splting documents in small chunks with overlap'''
    print("chunking documents....")

    text_spliter=CharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    chunks=text_spliter.split_documents(documents)

    if chunks:
        for i,chunk  in enumerate(chunks[:5]):
            print(f"------chunk {i+1} ------")
            print(f" Source: {chunk.metadata['source']}")
            print(f" Content Length: {len(chunk.page_content)} characater")
            print("Content :")
            print(chunk.page_content)
            print("-"*50)

            if len(chunks)>5:
                print(f"\n...and {len(chunks)-5}  more chunks....")
    
    return chunks


def vector_store(chunks,persist_directory="db/chroma_db"):
    '''Creating and persisting the chromaDb vector store'''
    print("Creating embedding and storing in chromaDB....")
    
    embedding_model=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    print("--------Creating Vector Store-------")
    vector_store=Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=persist_directory,
        collection_metadata={"hnsw:space": "cosine"}
    )
    print("--------Finished to creating vetor store -------")
    print(f"Vector store creted and save at {persist_directory}")
    return vector_store
        




def main():
    print("Main function")

    #loading documents
    documents=load_documents(docs_path="docs")

    #chinking 
    chunks=split_documents(documents)
    
    #store vector data
    vector_store(chunks)



if __name__=="__main__":
    main()