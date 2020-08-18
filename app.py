import hmac
import hashlib
import time
import yaml
from flask import Flask, Response, render_template, request
from flask_talisman import Talisman
from kubernetes import client, config
from github import Github

app = Flask(__name__, template_folder="")
csp = {
	"default-src": "'self'",
	"style-src": ["'self'", "https://tools-static.wmflabs.org"],
	"font-src": "https://tools-static.wmflabs.org"
}
talisman = Talisman(app, content_security_policy=csp, force_https=False, content_security_policy_nonce_in=["style-src"])
try:
	app.config.update(yaml.safe_load(open("/data/project/goodbot/secrets.yaml")))
	config.load_kube_config()
except Exception as e:  # to pass tests in non-Kubernetes context
	app.logger.info(e)
apps_v1 = client.AppsV1Api()
app.logger.info("Client loaded...")


@app.route("/deploy", methods=["POST"])
def respond():
	def validate_signature():
		key = bytes(app.config["webhook_secret"], "utf-8")
		expected_signature = hmac.new(key=key, msg=request.data, digestmod=hashlib.sha1).hexdigest()
		incoming_signature = request.headers.get("X-Hub-Signature").split("sha1=")[-1].strip()
		if not hmac.compare_digest(incoming_signature, expected_signature):
			return Response(status=400)
	if app.config.get("webhook_secret"):
		validate_signature()
	content = request.get_json(force=True)
	app.logger.info(f"{str(content)} request")
	try:
		check = content["check_suite"]
		sha = Github().get_repo("QEDK/goodbot").get_branch("master").commit.sha
		if check["head_sha"] == sha and check["conclusion"] == "success" and check["app"]["slug"] == "travis-ci":
			app.logger.info("Starting deployment...")
			api_response = apps_v1.delete_namespaced_deployment(
				name="goodbot.goodbot", namespace="tool-goodbot", body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=1))
			app.logger.info(f"Deployment deleted. status={str(api_response.status)}")
			api_response = apps_v1.delete_namespaced_deployment(
				name="goodbot.ircbot", namespace="tool-goodbot", body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=1))
			app.logger.info(f"Deployment deleted. status={str(api_response.status)}")
			time.sleep(60)
			with open("/data/project/goodbot/goodpod.yaml") as f:
				dep = yaml.safe_load(f)
				resp = apps_v1.create_namespaced_deployment(body=dep, namespace="tool-goodbot")
				app.logger.info(f"Deployment created. status={resp.metadata.name}")
			with open("/data/project/goodbot/ircpod.yaml") as f:
				dep = yaml.safe_load(f)
				resp = apps_v1.create_namespaced_deployment(body=dep, namespace="tool-goodbot")
				app.logger.info(f"Deployment created. status={resp.metadata.name}")
	except Exception as e:
		app.logger.info(e)
	return Response(status=200)


@app.route("/")
def index():
	return render_template("index.html")


if __name__ == "__main__":
	app.run(ssl_context="adhoc")
