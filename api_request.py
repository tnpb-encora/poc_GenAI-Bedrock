from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import requests
import os

class k8s_request():

    # def __init__(self):
    def __init__(self, user_query, key):
        # Necessary certificates
        self.ca_cert_path = os.path.abspath("certs/ca.crt")
        self.client_cert_path = os.path.abspath("certs/apiserver-kubelet-client.crt")
        self.client_key_path = os.path.abspath("certs/apiserver-kubelet-client.key")

        # Namespaces to be ignored
        self.excluded_namespaces = ["armada", "cert-manager", "flux-helm", "kube-system"]

        # API key
        self.api_key = key

        # Necessary API address
        self.api_server_url = "https://192.168.206.1:6443"

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
        llm = ChatOpenAI(openai_api_key = self.api_key)

        # Expected llm response format
        format_response = "api: <api_completion>"

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an API generator, based on the user input you will sugest the best API endpoint to retrieve the information from a kubernetes cluster.\n\nYou will only provide the API information that comes after the IP:PORT.\n\nMake sure the providade endpoint is a valid one.\n\nAlso make sure to only provide the API endpoint following the format: {format_response}."),
        ("user", "{input}")
        ])

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        # Get completion
        completion = chain.invoke({"input": self.query})
        clean_completion = completion.split(":")[1].strip()

        return clean_completion

    def filter_response(self, response):
        pods = response.json().get('items', [])
        filtered_pods = [
            pod for pod in pods if pod['metadata']['namespace'] not in self.excluded_namespaces]

        return filtered_pods

    def get_API_response(self):
        # Define Kubernetes API endpoint
        api_endpoint = self.get_endpoint()

        # Load Kubernetes certificates
        cert = (self.client_cert_path, self.client_key_path)
        verify = self.ca_cert_path

        # API request
        response = requests.get(api_endpoint, cert=cert, verify=verify)

        if response.status_code == 200:
            # Filter response for undesired namespaces
            filtered_response = self.filter_response(response)
            buit_text_response = f"API {api_endpoint} response = {filtered_response}"
            return buit_text_response
        else:
            print(f"Error trying to make API request:\n {response.status_code}, {response.text}")


class stx_request():
    pass


class openstack_request():
    pass

# test = k8s_request()
# k8s_request.get_API_response(test)