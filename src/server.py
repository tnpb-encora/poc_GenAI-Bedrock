from flask import Flask, request, jsonify
from flask_restful import Resource, Api
import app as chat
import sys


app = Flask(__name__)
api = Api(app)


class Users(Resource):
    def post(self):
        question = request.json['message']
        if question.lower() == "exit":
            sys.exit(0)
        answer = chat.ask(question)
        return jsonify(answer)


api.add_resource(Users, '/')

if __name__ == "__main__":
    chat.set_openai_key()
    chat.initiate_generator()
    app.run(port=2000)