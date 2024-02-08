import datetime
import json
import logging
import os
import re
import sys
import uuid
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.document import Document
from langchain.memory.buffer import ConversationBufferMemory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from api_request import k8s_request, stx_request
from openai import OpenAI
from constants import CLIENT_ERROR_MSG, LOG


def initiate_sessions():
    global sessions
    sessions = {}
    global node_list
    node_list = create_instance_list()


def get_session(session_id):
    return sessions.get(session_id)


def new_session(model, temperature):
    # Create vectorstore
    llm = ChatOpenAI(
        model_name=model,
        temperature=float(temperature),
        openai_api_key=OPENAI_API_KEY)
    session_id = str(uuid.uuid4())
    memory, retriever = create_vectorstore(llm)
    # Create chat response generator
    generator = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)

    # Give the LLM date time context
    query = f"From now on you will use {datetime.datetime.now()} as current datetime for any datetime related user query"
    generator.invoke(query)

    # Add session to sessions map
    sessions[session_id] = {"generator": generator, "llm": llm, "id": session_id}
    LOG.info(f"New session with ID: {session_id} initiated. Model: {model}, Temperature: {temperature}")
    return sessions[session_id]


def create_logger():
    # Create logger
    LOG = logging.getLogger("chatbot")
    LOG.setLevel(logging.INFO)

    # Create a file handler and set its level to INFO
    file_handler = logging.FileHandler('chatbot.log')
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    LOG.addHandler(file_handler)
    LOG.info("Chatbot logger initiated.")


def create_vectorstore(llm):
    # Create Chroma vector store
    data_start = "start vectorstore"
    docs = [Document(page_content=x) for x in data_start]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    memory = ConversationBufferMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    return memory, retriever


def ask(query, session):
    query_completion = query + ". If an API response is provided as context and in the provided API response doesn't have this information or no context is provided, make sure that your response is 'I don't know'."
    LOG.info(f"User query: {query}")
    response = session['generator'].invoke(query_completion)

    print(f'######{response}', file=sys.stderr)
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt_status = client.chat.completions.create(model='gpt-4',
                                                   messages=[{"role": "system",
                                                              "content": "Your role is to analyze the context of a text. You should check whether the text indicates that there is information about a subject or not. If the text contains expressions like 'Im sorry', or 'no context', or 'no information', or 'i don't know', perhaps it is saying that there is not enough information, therefore the context is negative. A context will also be negative if the text says that it doesn't have access to the information."},
                                                             {"role": "user",
                                                              "content": f"Based on the following text, check if the general context indicates that there is information about what is being asked or not. Make sure to answer only the words 'positive' if there is information, or 'negative' if there isn't. Don't answer nothing besides it: {response['answer']}"}])
    print(f'prompt status: {prompt_status.choices[0].message.content}', file=sys.stderr)
    if 'negative' in prompt_status.choices[0].message.content.lower():
        LOG.info("Negative response from LLM")
        feed_vectorstore(query, session)
        response = session['generator'].invoke(query)

    # if "I'm sorry" in response['answer'] or "there is no information" in response['answer'] or "I don't know" in response['answer']:
    #     feed_vectorstore(query, session)
    #     response = session['generator'].invoke(query_completion)
    LOG.info(f"Chatbot response: {response['answer']}")
    return response['answer']


def feed_vectorstore(query, session):
    response = api_response(query, session)

    if response is None:
        raise Exception('API response is null')

    print(f'API response: {response}', file=sys.stderr)

    regex = r"(?=.*\binternal\b)(?=.*\bserver\b)(?=.*\berror\b).+"
    if re.search(regex, response.lower()):
        response = CLIENT_ERROR_MSG

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    all_splits = text_splitter.split_text(response)
    docs = [Document(page_content=x) for x in all_splits]
    vectorstore = Chroma.from_documents(documents=docs, embedding=OpenAIEmbeddings(openai_api_key = OPENAI_API_KEY))

    llm = session['llm']

    memory = ConversationBufferMemory(
    llm=llm, memory_key="chat_history", return_messages=True)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 1})

    sessions[session['id']]['generator'] = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory)


def set_openai_key():
    create_logger()
    try:
        global OPENAI_API_KEY
        OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
        is_api_key_valid(OPENAI_API_KEY)
    except Exception:
        raise Exception("Error while trying to set OpenAI API Key variable")
    LOG.info("API key configured")
    return True


def is_api_key_valid(key):
    try:
        client = OpenAI(api_key=key)
        _ = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "This is a test."}],
            max_tokens=5
        )
    except Exception:
        raise Exception("The provided key is not valid.")
    return True


def define_api_pool(query, session):
    # Use LLM to decide if Kubernetes or StarlingX API pool should be used.
    complete_query = f"Based on the following query you will choose between StarlingX APIs and Kubernetes APIs. You will not provide that specific API, only inform if it is a Starlingx or a Kubernetes API. Make sure that your response only contains the name StarlingX or the name Kubernetes and nothing else.\n\nUser query: {query}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an AI connected to a StarlingX system and based on the user query you will define which set of APIs is best to retrieve the necessary information to answer the question."),
        ("user", "{input}")
    ])

    output_parser = StrOutputParser()
    chain = prompt | session["llm"] | output_parser
    response = chain.invoke({"input": complete_query})

    print(f"###########{response}")
    if response.lower() == "kubernetes":
        return "Kubernetes"
    elif response.lower() == "starlingx":
        return "StarlingX"
    else:
        return "Undefined"


def api_response(query, session):
    instance = define_system(query)
    print(f'Query being made to {instance["name"]}', file=sys.stderr)
    LOG.info(f'Query being made to {instance["name"]}')

    print('Defining API pool', file=sys.stderr)
    LOG.info('Defining API pool')
    pool = define_api_pool(query, session)
    print(f'LLM defined {pool} as the API subject', file=sys.stderr)
    LOG.info(f'LLM defined {pool} as the API subject')
    if pool == "Kubernetes":
        bot = k8s_request(query, OPENAI_API_KEY, instance)
        response = k8s_request.get_API_response(bot)
    elif pool == "StarlingX":
        bot = stx_request(query, OPENAI_API_KEY, instance)
        response = stx_request.get_API_response(bot)
    else:
        response = CLIENT_ERROR_MSG

    return response


def define_system(query):
    # Initiate OpenAI
    llm = ChatOpenAI(openai_api_key = OPENAI_API_KEY, model= "gpt-4-turbo-preview",temperature=0)

    # Get list of all instances
    instance_list = node_list
    print(f"\n\n\n{instance_list}\n\n")

    # Expected llm response format
    format_response = "name: <name>,URL: <URL>,type: <type>,token: <token>"

    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"Pretend that you are a system that choses a node in a Distributed Cloud environment.\nYour job is to define which of the instances in the context the user is asking about. Make sure that only 1 is given in your response, the answer will never be more than 1 instance. If the user did not specified which instance he wants the information, you will provide the information of the instance that contains central cloud as type.\nYour answer will follow the format: {format_response}"),
        ("user", "Context:{context} \n\n\n Question:{question}")
    ])

    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser

    #Get completion
    completion = chain.invoke({"context":instance_list, "question": query})
    print(f"#######{completion}")

    pairs = completion.split(',')
    node_dict = {}

    # Iterate over each key-value pair
    for pair in pairs:
        # Split each pair based on colon
        key, value = pair.split(':')

        # Remove leading and trailing whitespaces from key and value
        key = key.strip()
        value = value.strip()

        # Assign key-value pair to the dictionary
        node_dict[key] = value

    return node_dict


def create_instance_list():
    # Create list
    instance_list = []

    # Add the system controller as first item on the list
    controller = {"name":"System Controller",
                  "URL":os.environ['OAM_IP'],
                  "type":"central cloud",
                  "token":os.environ['TOKEN']}
    instance_list.append(controller)

    try:
        # Load subclouds information
        with open("subclouds.json", "r") as f:
            data = json.load(f)

        for item in data:
            new_subcloud = {
            "name": item["name"],
            "URL": item["URL"],
            "type": "subcloud",
            "token": item["k8s_token"]
            }

            instance_list.append(new_subcloud)
    except:
        LOG.warning("No subcloud information was added to the list of instances")

    return instance_list
