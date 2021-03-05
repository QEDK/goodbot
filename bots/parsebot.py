#!/usr/bin/env python3
import html2text
import json
import os
import re
import shlex
import subprocess
import sys
import time
from github import Github
from pathlib import Path
from requests import Session


def scan(session):
	projects = {}

	with open(str(Path(__file__).parents[1].joinpath("config", "config.json")), "r") as file:
		ideapages = json.load(file)["ideas"]

	for key in ideapages:
		projects[key] = {}
		i = 0
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
				projects[key].update({match.group("title").strip(): match.group("inner").strip()})

	with open(str(Path(__file__).parents[2].joinpath("projects.json")), "r") as outfile:
		current = json.load(outfile)
		if current == projects:
			return False

	with open(str(Path(__file__).parents[1].joinpath("templates", "projects.json")), "w") as outfile:
		json.dump(projects, outfile, indent="\t", sort_keys=True)

	with open(str(Path(__file__).parents[2].joinpath("projects.json")), "w") as outfile:
		json.dump(projects, outfile, indent="\t", sort_keys=True)

	return True


def commit():
	commands = ["git add templates/projects.json", "git commit -m \"Update projects.json\"", "git push origin parsebot"]
	for cmd in commands:
		subprocess.run(shlex.split(cmd))


def make_pull():
	repo = Github(os.environ.get("gitpat")).get_repo("QEDK/goodbot")  # gitpat is parsebot's personal access token
	return repo, repo.create_pull(title="Update project list", body="parsebot 🤖 hard at work 🛠️", head="parsebot", base="master", maintainer_can_modify=True)


def monitor(session, repo, pull):
	flag = True
	if repo.get_pull(pull.number).state == "closed":
		subprocess.run(shlex.split("git push origin -d parsebot"))
		flag = False
	scan(session)
	return flag


def main():
	session = Session()
	commands = ["git pull origin", "git checkout -b parsebot"]
	for cmd in commands:
		subprocess.run(shlex.split(cmd))
	if scan(session):
		commit()
		repo, pull = make_pull()
		while monitor(session, repo, pull):
			time.sleep(60)
	subprocess.run(shlex.split("git checkout master", "git branch -D parsebot"))
	sys.exit(0)


if __name__ == "__main__":
	main()
