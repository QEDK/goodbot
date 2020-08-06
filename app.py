from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/deploy', methods=['POST'])
def respond():
	print(request.json)
	return Response(status=200)

@app.route('/')
def index():
	return "Hello world"