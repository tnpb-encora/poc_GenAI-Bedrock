from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from main import OPENAI_API_KEY
import requests

class k8s_request():

    def __init__(self, user_query):
        # Necessary certificates
        self.ca_cert_path = "./certs/cacert.crt"
        self.client_cert_path = "./certs/apiserver-kubelet-client.crt"
        self.client_key_path = "./certs/apiserver-kubelet-client.key"

        # Namespaces to be ignored
        self.label_selector = 'namespace notin (armada, cert-manager, flux-helm, kube-system)'

        # Necessary API address
        self.api_server_url = "https://localhost:6443"

        # User query
        self.query = user_query



    def get_endpoint(self):
        completion = self.get_api_completion()
        if completion[0] == "/":
            api_endpoint = f'{self.api_server_url}{completion}'
        else:
            api_endpoint = f'{self.api_server_url}/{completion}'

        return api_endpoint

    def get_api_completion(self):
        # Initiate OpenAI
        llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY)

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an API generator, based on the user input you will sugest the best API endpoint to retrieve the information from a kubernetes cluster. You will only provide the API information that comes after the IP:PORT. Make sure to only provide the API endpoint and nothing more in your answer"),
        ("user", "{input}")
        ])

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        # Get completion
        completion = chain.invoke({"input": self.query})

        return completion

    def get_API_response(self):
        # Define Kubernetes API endpoint
        api_endpoint = self.get_endpoint(self.api_server_url)

        # Define params for the API request
        params = {'labelSelector': self.label_selector}

        # Load Kubernetes certificates
        cert = (self.client_cert_path, self.client_key_path)
        verify = self.ca_cert_path

        # API request
        response = requests.get(api_endpoint, cert=cert, verify=verify, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error trying to make API request:\n {response.status_code}, {response.text}")


class stx_request():
    pass


class openstack_request():
    pass