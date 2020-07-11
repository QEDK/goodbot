#!/usr/bin/env python3
from github import Github
from pathlib import Path
import subprocess
import html2text
import requests
import shlex
import json
import time
import re
import os


def scan(r):
	projects = dict()
	i = 0
	while True:
		i += 1
		params = {
			"action": "parse",
			"page": "Google Summer of Code/2020/Ideas for projects",
			"section": i,
			"prop": "text",
			"disablelimitreport": "true",
			"disableeditsection": "true",
			"disabletoc": "true",
			"format": "json"
		}
		req = r.get(url="https://www.mediawiki.org/w/api.php", params=params)
		try:
			if req.json()["error"]:
				break
		except KeyError:
			text = html2text.HTML2Text().handle(req.json()["parse"]["text"]["*"])
			match = re.search(r"#{1,}(?P<title>.*?\n)(?P<inner>.*)", text, flags=re.DOTALL)
			projects[match.group("title").strip()] = match.group("inner").strip()

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
	if scan(session):
		commit(first=False)
		if repo.get_pull(pull.number).state == "closed":
			commands = ["git push origin -d parsebot", "git stash", "git checkout master", "git branch -D parsebot"]
			for cmd in commands:
				subprocess.run(shlex.split(cmd))
			return False
	return True


def main():
	session = requests.Session()
	if scan(session):
		commit(first=True)
		repo, pull = make_pull()
		while monitor(session, repo, pull):
			time.sleep(60)
	exit(0)


if __name__ == "__main__":
	main()
