#!/usr/bin/env python3
import html2text
import json
import os
import re
import shlex
import subprocess
import time
from github import Github
from pathlib import Path
from requests import Session


def scan(session):
	projects = {}
	i = 0
	with open(Path(__file__).parents[1].joinpath("config", "config.json"), "r") as file:
		ideapages = json.load(file)["ideas"]
	for key in ideapages:
		while True:
			i += 1
			params = {
				"action": "parse",
				"page": ideapages[key],
				"section": i,
				"prop": "text",
				"disablelimitreport": "true",
				"disableeditsection": "true",
				"disabletoc": "true",
				"format": "json"
			}
			req = session.get(url="https://www.mediawiki.org/w/api.php", params=params)
			try:
				if req.json()["error"]:
					break
			except KeyError:
				text = html2text.HTML2Text().handle(req.json()["parse"]["text"]["*"])
				match = re.search(r"#{1,}(?P<title>.*?\n)(?P<inner>.*)", text, flags=re.DOTALL)
				projects[key][match.group("title").strip()] = match.group("inner").strip()

	with open(Path(__file__).parents[1].joinpath("templates", "projects.json"), "r") as outfile:
		current = json.load(outfile)
		if current == projects:
			return False

	with open(Path(__file__).parents[1].joinpath("templates", "projects.json"), "w") as outfile:
		json.dump(projects, outfile, indent="\t", sort_keys=True)
		return True


def commit(first):
	if first:
		commands = ["git pull origin", "git checkout -b parsebot"]
		for cmd in commands:
			subprocess.run(shlex.split(cmd))
	commands = ["git add templates/projects.json", "git commit -m Update projects.json", "git push origin parsebot"]
	for cmd in commands:
		subprocess.run(shlex.split(cmd))


def make_pull():
	repo = Github(os.environ.get("gitpat")).get_repo("QEDK/goodbot")
	return repo, repo.create_pull(title="Update project list", body="parsebot 🤖 hard at work 🛠️", head="parsebot", base="master", maintainer_can_modify=True)


def monitor(session, repo, pull):
	if repo.get_pull(pull.number).state == "closed":
		subprocess.run(shlex.split("git push origin -d parsebot"))
		return False
	if scan(session):
		commit(first=False)
	return True


def main():
	session = Session()
	if scan(session):
		commit(first=True)
		repo, pull = make_pull()
		while monitor(session, repo, pull):
			time.sleep(60)
	exit(0)


if __name__ == "__main__":
	main()
