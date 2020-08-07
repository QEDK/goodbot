from flask import Flask, Response, request, send_from_directory
from flask_talisman import Talisman

app = Flask(__name__)
csp = {
	"default-src": "'self'",
	"style-src": "https://tools-static.wmflabs.org"
}
talisman = Talisman(app, content_security_policy=csp)


@app.route("/deploy", methods=["POST"])
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
	return send_from_directory("", "index.html")
