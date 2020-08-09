from flask import Flask, Response, render_template, request
from flask_talisman import Talisman
from kubernetes import client, config
import yaml
import time
import logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, template_folder="")
app.config.update({"ENV": "development", "DEBUG": True})
csp = {
	"default-src": "'self'",
	"style-src": ["'self'", "https://tools-static.wmflabs.org"],
	"font-src": "https://tools-static.wmflabs.org"
}
talisman = Talisman(app, content_security_policy=csp, force_https=False, content_security_policy_nonce_in=["style-src"])
try:
	config.load_kube_config()
except Exception as e:  # to pass tests in non-Kubernetes context
	app.logger.info(e)
apps_v1 = client.AppsV1Api()
app.logger.info("Client loaded...")


@app.route("/deploy", methods=["POST"])
def respond():
	app.logger.info(f"{str(request)} request")
	content = request.get_json(force=True)
	try:
		if content["head_branch"] == "dev" and content["conclusion"] == "success" and content["app"]["slug"] == "travis-ci":
			app.logger.info("Starting deployment...")
			api_response = apps_v1.delete_namespaced_deployment(
				name="goodbot.goodbot", namespace="tool-goodbot", body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=1))
			app.logger.info("Deployment deleted. status='%s'" % str(api_response.status))
			api_response = apps_v1.delete_namespaced_deployment(
				name="goodbot.ircbot", namespace="tool-goodbot", body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=1))
			app.logger.info("Deployment deleted. status='%s'" % str(api_response.status))
			time.sleep(60)
			with open("/data/project/goodbot/goodpod.yaml") as f:
				dep = yaml.safe_load(f)
				resp = apps_v1.create_namespaced_deployment(body=dep, namespace="tool-goodbot")
				app.logger.info("Deployment created. status='%s'" % resp.metadata.name)
			with open("/data/project/goodbot/ircpod.yaml") as f:
				dep = yaml.safe_load(f)
				resp = apps_v1.create_namespaced_deployment(body=dep, namespace="tool-goodbot")
				app.logger.info("Deployment created. status='%s'" % resp.metadata.name)
	except Exception as e:
		app.logger.info(e)
	return Response(status=200)


@app.route("/")
def index():
	return render_template("index.html")


if __name__ == "__main__":
	app.run(ssl_context="adhoc", debug=True)
