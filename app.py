from langchain.chains import ConversationalRetrievalChain
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.schema.document import Document
from langchain.memory import ConversationSummaryMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from api_request import k8s_request
from openai import OpenAI
import os

### To locally test the app ,uncomment this function and the last two lines of this file
# def main():
#     set_openai_key()
#     initiate_generator()
#     query = input()
#     ask(query)


def initiate_generator():
    # Initiate LLM
    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY)
    # Create vectorstore
    memory, retriever = create_vectorstore(llm)
    # Create chat response generator
    global generator
    generator = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)


def create_vectorstore(llm):
    # Create Chroma vector store
    data_start = "start vectorstore"
    docs = [Document(page_content=x) for x in data_start]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    memory = ConversationSummaryMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    return memory, retriever


def ask(query):
    query += ". If an API response is provided as context and in the provided API response doesn't have this information or no context is provided, make sure that your response is 'I don't know'."
    response = generator.invoke(query)
    if "I'm sorry" in response['answer'] or "there is no information" in response['answer']:
        feed_vectorstore(query)
        response = generator.invoke(query)
        print(response['answer'])
    else:
        print(response['answer'])
    ## Uncommnet to test locally
    # query = input().lower()


def feed_vectorstore(query):
    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY)
    bot = k8s_request(query, OPENAI_API_KEY)
    response = k8s_request.get_API_response(bot)

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    all_splits = text_splitter.split_text(response)
    docs = [Document(page_content=x) for x in all_splits]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    memory = ConversationSummaryMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    global generator
    generator = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)


def get_openai_key():
    print("Hello! This is the chatbot for your StarlingX cluster.")
    print("To procced, you need to provide an OpenAI API key:")
    valid_key = False

    while valid_key == False:
        api_key = input()
        valid_key = is_api_key_valid(api_key)
        if valid_key == False:
            print("The provided key is not valid."
                  "Please provide a valid OpenAI API key:")

    print("Thank you! If at any point you want to close the chatbot just type 'exit'")

    return api_key


def set_openai_key():
    global OPENAI_API_KEY
    if os.environ.get('OPENAI_API_KEY'):
        OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
    else:
        OPENAI_API_KEY = get_openai_key()


def is_api_key_valid(key):
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "This is a test."}],
            max_tokens=5
        )
    except:
        return False
    else:
        return True


# if __name__ == "__main__":
#     main()