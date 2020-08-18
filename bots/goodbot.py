#!/usr/bin/env python3
import configparser
import json
import os
import random
import re
import shlex
import subprocess
import wikipedia
import zulip
from stackapi import StackAPI
from rapidfuzz import fuzz
from rapidfuzz import process as fuzzproc
from pathlib import Path


class goodbot(object):
	def __init__(self, config_file="~/zuliprc"):
		config = configparser.ConfigParser()
		config.read(os.path.abspath(os.path.expanduser(config_file)))
		config = config["api"]
		self.bot_mail = config.get("email")
		self.client = zulip.Client(config_file=config_file)
		with open(Path(__file__).parents[1].joinpath("templates", "faq.json")) as file:
			self.faqs = json.load(file)
		with open(Path(__file__).parents[1].joinpath("templates", "replies.json")) as file:
			self.replies = json.load(file)
		with open(Path(__file__).parents[1].joinpath("templates", "projects.json")) as file:
			self.projects = json.load(file)
			self.flatprojects = {}
			idx = 1
			for key in self.projects:
				for title in self.projects[key]:
					self.flatprojects[idx] = (title, self.projects[key][title])
					idx += 1
		with open(Path(__file__).parents[1].joinpath("config", "config.json")) as file:
			self.config = json.load(file)
		self.questions = list(question for question in self.faqs["questions"])
		self.answers = self.faqs["answers"]
		self.greetings = self.replies["greetings"]
		self.subscribe_all()
		print("Bot init complete")

	def subscribe_all(self):
		allstreams = self.client.get_streams()["streams"]
		streams = [{"name": stream["name"]} for stream in allstreams]
		self.client.add_subscriptions(streams)
		print("Subscription complete")

	def subscribe_user(self, stream, user_email):
		self.client.add_subscriptions(streams=[{"name": stream}], principals=[user_email])

	def fuzzymatch(self, faq):
		answer = fuzzproc.extractOne(faq, self.questions, scorer=fuzz.token_sort_ratio)
		if answer[1] > 60:
			print(answer)
			return self.answers[self.faqs["questions"][answer[0]]]
		else:
			return None

	def process(self, msg):
		sender_email = msg["sender_email"]
		if sender_email == self.bot_mail:  # quick return
			return
		content = msg["content"].strip().split()
		sender_full_name = msg["sender_full_name"]
		message_type = msg["type"]  # "stream" or "private"
		if message_type == "stream":
			destination = msg["stream_id"]  # destination is stream
		else:
			destination = sender_email  # destination is PM
		topic = msg["subject"]  # topic legacy naming in API

		print(str(content) + "\nSuccessfully heard.")

		try:
			greeting = f"{random.choice(self.greetings)} @**{sender_full_name}**!"
			if sender_email == "notification-bot@zulip.com" and topic == "signups":  # hack for reading #announce stream
				userid = re.search(r"\|(?P<id>\d+)\*\*", msg["content"])
				if userid is None:
					return
				self.client.send_message({
					"type": "private",
					"to": f"[{userid.group('id')}]",
					"content": f"{self.replies['welcome']}"
				})

			def help():
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} {self.replies['helptext']}"
				})

			def gsoc():
				page = self.config["pages"]["gsoc"]
				stream = self.config["streams"]["gsoc"]
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} test {self.replies['gsoc'].format(page=page, stream=stream)}"
				})
				self.subscribe_user(stream, sender_email)

			def gsod():
				page = self.config["pages"]["gsod"]
				stream = self.config["streams"]["gsod"]
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} test {self.replies['gsod'].format(page=page, stream=stream)}"
				})
				self.subscribe_user(stream, sender_email)

			def outreachy():
				page = self.config["pages"]["outreachy"]
				stream = self.config["streams"]["outreachy"]
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} test {self.replies['outreachy'].format(page=page, stream=stream)}"
				})
				self.subscribe_user(stream, sender_email)

			def faq():
				if len(content) == 1:
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} You can ask me a question by adding the question after the command: `!faq 'your question'`"
					})
					return
				lookup = self.fuzzymatch(" ".join(content[2:]))
				if lookup is None:
					return
				else:
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} {lookup}"
					})

			def wikisearch():
				if len(content) == 1:
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} You can make me search Wikipedia by adding the query after the command: `!wikipedia 'your query'`"
					})
					return
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} {self.replies['wait']}"
				})
				query = " ".join(content[1:])
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} Got it! :point_right: {wikipedia.summary(query, sentences=2)}"  # summary is a very slow call
				})
				response = ""
				for result in wikipedia.search(query, results=1):
					page = wikipedia.page(result)
					response += f"* [{page.title}]({page.url})"
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": response
				})

			def stackoverflowsearch():
				if len(content) == 1:
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} You can make me search StackOverflow by adding the query after the command: `!stackoverflow 'your query'`"
					})
					return
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} {self.replies['wait']}"
				})
				query = " ".join(content[1:])
				stackoverflow = StackAPI('stackoverflow')
				stackoverflow.page_size = 3  # lesser, the faster
				stackoverflow.max_pages = 1  # will hit API only once
				questions = stackoverflow.fetch('search/advanced', sort="relevance", q=query, order="desc", answers=1)
				response = f"**Closest match:** {questions['items'][0]['title']}"
				try:
					answerjson = stackoverflow.fetch('answers/{ids}', ids=[str(questions['items'][0]['accepted_answer_id'])], filter="!9Z(-wzftf")  # filter code: default+"answer.body_markdown"
					answer = "\n**Accepted answer:**\n" + answerjson['items'][0]['body_markdown']
				except IndexError:  # faster than checking if index exists
					answer = "\n**No accepted answer found**"
				response += f"{answer}\nOther questions:\n"
				response += "\n".join((f"* [{question['title']}]({question['link']})") for question in questions['items'][1:])
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{greeting} Got it! :point_down:\n{response}"
				})

			def chat():
				response = self.replies["chathelp"]
				self.subscribe_user("technical-support", sender_email)
				try:
					response = self.replies[content[1].lower()]
				except Exception:
					pass
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{greeting} {response}"
				})

			def projects():
				if len(content) == 1:
					response = "Here's the list of projects:\n"
					idx = 1
					for key in self.projects:
						if key == "gsocideas":
							response += "**Google Summer of Code -**\n"
						else:
							response += "**Outreachy -**\n"
						for title in self.projects[key]:
							response += f"{idx}. {title}\n"
							idx += 1
					response += f"{self.replies['projectdetails']}"
				else:
					choice = re.match(r"\d+", content[1])
					if choice is not None:
						try:
							title, description = self.flatprojects[int(choice.group(0))]
							response = f"**{title}**\n {description}"
						except KeyError:
							response = f"{self.replies['invalidproject']}"
					else:
						response = f"{self.replies['projectdetails']}"
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{greeting} {response}"
				})

			def contact():
				response = ""
				for admin, email in self.config["orgadmins"].items():
					response += f"@_**{admin}** {email}\n"
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{greeting} Here you go :point_down:\n{response}"
				})

			def ping():
				response = ""
				for admin, email in self.config["orgadmins"].items():
					response += f"@**{admin}** "
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{response} Need some help! :point_up:"
				})

			def config():
				response = self.replies["confighelp"]
				if sender_email not in self.config["botadmins"]:
					response = "You are not authorized to make this action."
				else:
					try:
						if content[1].lower() == "view":
							response = f"```json\n{json.dumps(self.config, indent=2)}\n```"
						elif content[1].lower() == "update":
							key, value = content[2].split(":", maxsplit=1)
							if key in self.config:
								try:
									copy = self.config.copy()
									copy[key] = json.loads(value)
									json.loads(json.dumps(copy))
									self.config[key] = json.loads(value)
									response = "Configuration updated successfully."
								except Exception as e:
									response = f"Input is not valid JSON. {e}"
							else:
								response = "Key does not exist in configuration."
						elif content[1].lower() == "commit":
							cmds = [
								"git add config/config.json",
								f"git commit -m {content[2]} --author={sender_email}",
								"git push origin --dry-run"
							]
							with open(Path(__file__).parents[1].joinpath("config", "config.json"), "w") as file:
								json.dump(self.config, file, indent="\t")
							for cmd in cmds:
								subprocess.run(shlex.split(cmd))
							response = "Committed to repository."
						elif content[1].lower() == "reset":
							with open(Path(__file__).parents[1].joinpath("config", "config.json")) as file:
								self.config = json.load(file)
							response = "Configuration reset successfully."
					except Exception:
						pass
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{response}"
				})

			if "goodbot" in content and content[0].lower() != "!help":
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{greeting} :blush: What can I do for you today?"
				})

			keywords = {
				"!help": help, "@**goodbot**": help, "!gsoc": gsoc, "!gsod": gsod, "!outreachy": outreachy, "!faq": faq,
				"!wikipedia": wikisearch, "!stackoverflow": stackoverflowsearch, "!chat": chat, "!projects": projects,
				"!contact": contact, "!ping": ping, "!config": config
			}
			keywords[content[0].lower()]()

		except Exception:
			pass


def main():
	print("Begin bot init")
	bot = goodbot(config_file="~/zuliprc")
	bot.client.call_on_each_message(bot.process)


if __name__ == "__main__":
	main()
