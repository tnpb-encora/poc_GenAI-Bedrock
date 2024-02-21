import sys

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from constants import CLIENT_ERROR_MSG, LOG
import requests
import re
import os

class k8s_request():

    # def __init__(self):
    def __init__(self, user_query, key, instance):
        # Get IP
        ip = instance['URL']
        pattern = r"(https?)://(?:\d{1,3}\.){3}\d{1,3}:"
        match = re.search(pattern, ip)
        self.oam_ip = match.group(0)

        # Get name
        self.name = instance['name']

        # Get Kubernetes TOKEN
        self.k8s_token = instance['token']

        # Namespaces to be ignored
        self.excluded_namespaces = ["armada", "cert-manager", "flux-helm", "kube-system"]

        # API key
        self.api_key = key

        # Necessary API address
        if "https" in self.oam_ip:
            self.api_server_url = f"{self.oam_ip}6443"
        else:
            secure_oam = self.oam_ip.replace("http://", "https://")
            self.api_server_url = f"{secure_oam}6443"

        # User query
        self.query = user_query


    def get_endpoint(self):
        completion = self.get_api_completion()
        if completion[0] == "/":
            api_endpoint = f'{self.api_server_url}{completion}'
        elif completion == "-1":
            return completion
        else:
            api_endpoint = f'{self.api_server_url}/{completion}'

        # Guarantee that chatbot don't use alucinated API for k8s version
        if "version" in api_endpoint:
            api_endpoint = f"{self.api_server_url}/version"

        return api_endpoint

    def get_api_completion(self):
        # Initiate OpenAI
        llm = ChatOpenAI(openai_api_key = self.api_key)

        # Expected llm response format
        format_response = "api: <api_completion>"

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an API generator, based on the user input you will suggest the best API endpoint to retrieve the information from a kubernetes cluster.\n\nYou will only provide the API information that comes after the IP:PORT.\n\nMake sure the provided endpoint is a valid one.\n\nAlso make sure to only provide the API endpoint following the format: {format_response}. Guarantee that the format is followed."),
        ("user", "{input}")
        ])

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        # Get completion
        completion = chain.invoke({"input": self.query})
        if len(completion.split(":")) > 1:
            clean_completion = completion.split(":")[1].strip()
        else:
            clean_completion = "-1"

        return clean_completion

    def filter_response(self, response):
        if response.json().get('items', []) != []:
            pods = response.json().get('items', [])
            try:
                filtered_pods = [
                    pod for pod in pods if pod['metadata']['namespace'] not in self.excluded_namespaces]
                return filtered_pods
            except:
                return response.json()
        else:
            return response.json()

    def get_API_response(self):
        # Define Kubernetes API endpoint
        api_endpoint = self.get_endpoint()
        if api_endpoint == "-1":
            return CLIENT_ERROR_MSG

        # Define headers with Authorization
        headers = {'Authorization': f'Bearer {self.k8s_token}'}

        # API request
        try:
            print(f'API address: {api_endpoint}', file=sys.stderr)
            LOG.info(f'API address: {api_endpoint}')
            response = requests.get(api_endpoint, headers=headers, verify=False)
        except Exception as e:
            error = f"An error ocurred while trying to retrieve the information, please rewrite the question and try again.\n Error: {e}"
            LOG.warning(error)
            return error

        if response.status_code == 200:
            # Filter response for undesired namespaces
            filtered_response = self.filter_response(response)
            buit_text_response = f"API {api_endpoint} response from {self.name} = {filtered_response}"
            return buit_text_response
        else:
            error = f"Error trying to make API request:\n {response.status_code}, {response.text}"
            LOG.warning(error)
            return error


class wr_request():

    def __init__(self, user_query, key, instance):
        # Load env variables
        self.auth_url = instance['URL']
        self.user = os.environ['WR_USER']
        self.password = os.environ['WR_PASSWORD']
        self.name = instance['name']
        self.type = instance['type']

        # Necessary API address
        pattern = r"(https?)://(?:\d{1,3}\.){3}\d{1,3}:"
        match = re.search(pattern, self.auth_url)
        self.api_server_url = match.group(0)

        # Necessary token
        self.token = self.get_token()

        # API key
        self.api_key = key

        # User query
        self.query = user_query

        # Embedded list of Wind River APIs
        self.apis = self.load_embedded_apis()


    def load_embedded_apis(self):
        with open ("wr_apis.json", "r") as f:
            api_list = f.read()

        return api_list


    def get_endpoint(self):
        completion = self.get_api_completion()
        api = self.api_server_url + completion

        return api


    def get_api_completion(self):
        # Initiate OpenAI
        llm = ChatOpenAI(openai_api_key = self.api_key,
                         temperature=0.4)

        # Expected llm response format
        format_response = "api: <api_url>"

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an API generator, based on the user question you will suggest the best API endpoint to retrieve the information from a Wind River cluster.\n\nYou will look in the context for the available APIs in a Wind River cluster.\n\nMake sure the provided endpoint is present on the provided context and check the action of the APIs to provide the ideal url for the user question. This user question is being made to a {self.type}.\n\nAlso make sure to only provide the API endpoint following the format: {format_response}. Guarantee that the format is followed. Read the entire context before providing an answer."),
        ("user", "Context:{context} \n\n\n Question:{question}")
        ])

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        #Get completion
        completion = chain.invoke({"context":self.apis, "question": self.query})

        #completion = response.choices[0].message.content
        clean_completion = completion.split(":")[1].strip()

        return clean_completion


    def get_API_response(self):
        url = self.get_endpoint()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Auth-Token": self.token
        }


        try:
            print(f'API address: {url}', file=sys.stderr)
            LOG.info(f'API address: {url}')
            response = requests.get(url, headers=headers, verify=False)
        except Exception as e:
            error = f"An error ocurred while trying to retrieve the information, please rewrite the question and try again.\n Error: {e}"
            LOG.warning(error)
            return error

        if response.status_code == 200:
            str_response = f"Wind River API response from {self.name} = {response.text}"
            return str_response
        else:
            error = f"Error trying to make API request:\n {response.status_code}, {response.text}"
            LOG.warning(error)
            return error



    def get_token(self):
        url = f"{self.auth_url}/v3/auth/tokens"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self.user,
                            "domain": {"id": "default"},
                            "password": self.password
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": "admin",
                        "domain": {"id": "default"}
                    }
                }
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data, verify=False)
        except Exception as e:
            error = f"An error ocurred while trying to retrieve the authentication for the Wind River APIs. Error:{e}"
            LOG.error(error)
            return error

        if response.status_code == 201:
            # Get token from response
            x_auth_token = response.headers["x-subject-token"]

            return x_auth_token
        else:
            error = f"Error trying to retrieve authentication token:\n {response.status_code}, {response.text}"
            LOG.warning(error)
            return error




class openstack_request():
    pass
