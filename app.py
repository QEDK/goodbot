from flask import Flask, request, Response
from subprocess import check_output

app = Flask(__name__)


@app.route("deploy", methods=["POST"])
def respond():
	content = request.get_json(silent=True)
	try:
		if content["successful"]:
			pass
	except KeyError:
		pass
	return Response(status=200)


@app.route("/")
def index():
	return check_output("kubectl get pods").decode("utf-8")
