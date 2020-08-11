import subprocess
from nose.tools import eq_, ok_
from app import app
import os
import signal


def test_zulip():
	proc = subprocess.Popen(["python3", "-u", "bots/goodbot.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	try:
		outs, errs = proc.communicate(timeout=10)
	except subprocess.TimeoutExpired:
		proc.kill()
		outs, errs = proc.communicate()
	outs = outs.decode()
	errs = errs.decode()
	eq_(len(errs), 0, errs)
	ok_("Begin bot init" in outs, "Bot init failed")
	ok_("Subscription complete" in outs, "Subscription failed")
	ok_("Bot init complete" in outs, "Bot init could not be completed")


def test_irc():
	proc = subprocess.Popen(["python3", "-u", "bots/ircbot.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
	try:
		outs, errs = proc.communicate(timeout=15)
	except subprocess.TimeoutExpired:
		os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  # force os to kill child processes
		outs, errs = proc.communicate()
	outs = outs.decode()
	errs = errs.decode()
	eq_(len(errs), 0, errs)
	ok_("Begin ircbot init" in outs, "ircbot init failed")
	ok_("Connected to IRC server" in outs, "Could not connect to IRC server")
	ok_("Joined IRC channel" in outs, "Could not join IRC channel")
	ok_("Connected to Zulip" in outs, "Could not connect to Zulip")


class test_flask():
	@classmethod
	def setUpClass(cls):
		pass

	@classmethod
	def tearDownClass(cls):
		pass

	def setUp(self):
		# creates a test client
		self.app = app.test_client()
		# propagate the exceptions to the test client
		self.app.testing = True

	def tearDown(self):
		pass

	def test_index_status_code(self):
		# sends HTTP GET request to the application
		# on the specified path
		result = self.app.get("/")

		# assert the status code of the response
		eq_(result.status_code, 200)

	def test_bad_deploy_post(self):
		# sends HTTP request to the application
		# on the specified path
		result = self.app.post("/deploy")

		# assert the response data
		eq_(result.status_code, 400)

	def test_good_deploy_post(self):
		# sends HTTP request to the application
		# on the specified path
		result = self.app.post("/deploy", data="{}")

		# assert the response data
		eq_(result.status_code, 200)
