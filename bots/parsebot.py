#!/usr/bin/env python3
import requests
import html2text

r = requests.Session()
projects = {}
i = 0
while True:
	i += 1
	params = {
		"action": "parse",
		"page": "Google Summer of Code/2020/Ideas for projects",
		"section": i,
		"prop": "text",
		"disableeditsection": "true",
		"disabletoc": "true",
		"format": "json"
		}
	req = r.get(url="https://www.mediawiki.org/w/api.php", params=params)
	try:
		if req.json()["error"]:
			break
	except KeyError:
		continue
print(req.json())
print(html2text.HTML2Text().handle(req.json()["parse"]["text"]["*"]))
