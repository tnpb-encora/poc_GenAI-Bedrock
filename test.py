import requests
import json

def test():

    api_endpoint = "https://192.168.206.1:6443/api/v1/pods"

    ca_cert_path = "/home/daniel-caires/poc_GenAI/certs/ca.crt"
    client_cert_path = "/home/daniel-caires/poc_GenAI/certs/apiserver-kubelet-client.crt"
    client_key_path = "/home/daniel-caires/poc_GenAI/certs/apiserver-kubelet-client.key"

    # Namespaces to be ignored
    label_selector = 'namespace notin (armada, cert-manager, flux-helm, kube-system)'

    # Define params for the API request
    params = {'labelSelector': label_selector}

    # Load Kubernetes certificates
    cert = (client_cert_path, client_key_path)
    verify = ca_cert_path

    # API request
    response = requests.get(api_endpoint, cert=cert, verify=verify, params=params)

    if response.status_code == 200:
        with open ("resposta.json", "w") as f:
            f.write(json.dumps(response.json()))
    else:
        print(f"Error: {response.status_code}, {response.text}")

test()