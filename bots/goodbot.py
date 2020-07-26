#!/usr/bin/env python3
import zulip
import wikipedia
from stackapi import StackAPI
import configparser
from rapidfuzz import fuzz
from rapidfuzz import process as fuzzproc
from pathlib import Path
import random
import json
import re
import os


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
		self.questions = list(question for question in self.faqs["questions"])
		self.answers = self.faqs["answers"]
		self.greetings = self.replies["greetings"].split(";")
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

			if content[0].lower() == "!help" or content[0] == "@**goodbot**":
				if(len(content) == 1):
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} {self.replies['helptext']}"
					})
				elif(len(content) > 1):
					content = content[1:]
					content[0] = f"!{content[0]}"

			if content[0].lower() == "!gsoc":
				self.subscribe_user("gsoc20-outreachy20", sender_email)
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} {self.replies['gsoc']}"
				})
			elif content[0].lower() == "!gsod":
				self.subscribe_user("gsod20", sender_email)
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} {self.replies['gsod']}"
				})
			elif content[0].lower() == "!outreachy":
				self.subscribe_user("gsoc20-outreachy20", sender_email)
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} {self.replies['outreachy']}"
				})
			elif content[0].lower() == "!faq":
				if(len(content) == 1):
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} You can ask me a question by adding the question after the command: `!help faq 'your question'`"
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
			elif content[0].lower() == "!wikipedia":
				if(len(content) == 1):
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} You can make me search Wikipedia by adding the query after the command: `!help wikipedia 'your query'`"
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
			elif content[0].lower() == "!stackoverflow":
				if(len(content) == 1):
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} You can make me search StackOverflow by adding the query after the command: `!help stackoverflow 'your query'`"
					})
					return
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} {self.replies['wait']}"
				})
				query = ' '.join(content[1:])
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
			elif content[0].lower() == "!chat":
				if(len(content) == 1):
					self.client.send_message({
						"type": message_type,
						"to": destination,
						"topic": topic,
						"content": f"{greeting} {self.replies['chathelp']}"
					})
					return
				if(content[1].lower() == "wikimedia"):
					self.subscribe_user("technical-support", sender_email)
					self.client.send_message({
						"type": message_type,
						"to": destination,
						"topic": topic,
						"content": f"{greeting} {self.replies['wikimedia']}"
					})
				if(content[1].lower() == "mediawiki"):
					self.subscribe_user("technical-support", sender_email)
					self.client.send_message({
						"type": message_type,
						"to": destination,
						"topic": topic,
						"content": f"{greeting} {self.replies['mediawiki']}"
					})
			elif content[0].lower() == "!projects":
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
					response += "You can see more details about the project by typing: `!projects <number>`."
				else:
					choice = re.match(r"\d+", content[1])
					if choice is not None:
						try:
							title, description = self.flatprojects[int(choice.group(0))]
							response = f"**{title}**\n {description}"
						except IndexError:
							response = "Invalid project number was entered."
					else:
						response = "You can see more details about the project by typing: `!projects <number>`."
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{greeting} {response}"
				})
			elif "goodbot" in content and content[0] != "!help":
				self.client.send_message({
					"type": message_type,
					"to": destination,
					"topic": topic,
					"content": f"{greeting} :blush: What can I do for you today?"
				})
			else:
				return
		except Exception as e:
			print(e)


def main():
	print("Begin bot init")
	bot = goodbot(config_file="~/zuliprc")
	bot.client.call_on_each_message(bot.process)


if __name__ == "__main__":
	main()
