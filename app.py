from flask import Flask, Response, request, send_from_directory
from flask_talisman import Talisman
from kubernetes import client, config
import yaml

app = Flask(__name__)
csp = {
	"default-src": "'self'",
	"style-src": "https://tools-static.wmflabs.org",
	"font-src": "https://tools-static.wmflabs.org"
}
talisman = Talisman(app, content_security_policy=csp, force_https=False)
try:
	config.load_kube_config()
except Exception as e:  # to pass tests in non-Kubernetes context
	print(e)
apps_v1 = client.AppsV1Api()


@app.route("/deploy", methods=["POST"])
def respond():
	content = request.get_json(silent=True)
	try:
		if content is not None and request.headers.get("Travis-Repo-Slug") == "QEDK/goodbot":
			api_response = apps_v1.delete_namespaced_deployment(
				name="goodbot.goodbot", namespace="default", body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=0))
			print("Deployment deleted. status='%s'" % str(api_response.status))
			with open("/data/project/ircpod.yaml") as f:
				dep = yaml.safe_load(f)
				resp = apps_v1.create_namespaced_deployment(body=dep, namespace="goodbot")
				print("Deployment created. status='%s'" % resp.metadata.name)
			api_response = apps_v1.delete_namespaced_deployment(
				name="goodbot.ircbot", namespace="default", body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=0))
			print("Deployment deleted. status='%s'" % str(api_response.status))
			with open("/data/project/goodpod.yaml") as f:
				dep = yaml.safe_load(f)
				resp = apps_v1.create_namespaced_deployment(body=dep, namespace="goodbot")
				print("Deployment created. status='%s'" % resp.metadata.name)
	except KeyError:
		pass
	return Response(status=200)


@app.route("/")
def index():
	return send_from_directory("", "index.html")


if __name__ == "__main__":
	app.run(ssl_context="adhoc")
