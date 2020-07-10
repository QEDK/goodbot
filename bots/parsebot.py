#!/usr/bin/env python3
import requests
import html2text
from github import Github
import json
from pathlib import Path
import re

r = requests.Session()
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
		continue

with open(Path(__file__).parents[1].joinpath("templates", "projects.json"), "w+") as outfile:
	current = json.load(outfile)
	if current == projects:
		exit(0)
	json.dump(projects, outfile, indent="\t", sort_keys=True)
