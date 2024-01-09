from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from respost import RESPOST

from openai import OpenAI

def main():

    OPENAI_API_KEY = get_openai_key()

    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are chatbot that provides information about a StarlingX system. Your answer is a succint paragraph answering exactly what the user asked. Make sure to use the chat history to provide your answer, like a conversation. Make sure to answer in the user query language."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])

    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser

    repeat = "yes"

    while repeat == "yes":
        ask(chain)
        print("Do you have more questions?(yes/no)")
        repeat = input().lower()

    print("Thank you for using the StarlingX chatbot!")


def ask(chain):
    print("What would like to know?")
    query = input()
    print(chain.invoke(
        {
            "chat_history": [
                HumanMessage(content="Retrieve information about the pods in my system"),
                AIMessage(content= RESPOST),
            ],
            "input": f"{query}"}))


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

    return api_key


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


if __name__ == "__main__":
    main()