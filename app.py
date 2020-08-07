from flask import Flask, request, Response
import subprocess

app = Flask(__name__)


@app.route('/deploy', methods=['POST'])
def respond():
	content = request.get_json(silent=True)
	try:
		if content["successful"]:
			pass
	except KeyError:
		pass
	return Response(status=200)


@app.route('/')
def index():
	return subprocess.run("kubectl get pods")
