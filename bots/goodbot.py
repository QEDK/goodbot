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
				username = re.search(r"\*\*.*\*\*", msg["content"])
				if username is None:
					return
				else:
					username = "@" + username.group(0)
				self.client.send_message({
					"type": message_type,
					"topic": topic,
					"to": destination,
					"content": f"{greeting} Welcome to Wikimedia Zulipchat.\nIf you need any help with GSoD proposals, type `!help gsod`.\nIf you need any help with GSoC proposals, type `!help gsoc`.\nIf you need help with Outreachy proposals, type `!help outreachy`.\nYou can join the #**technical-support** channel to get technical help related to Wikimedia infrastructure.\nType `!help` for a full list of available commands. :blush:"
				})

			if content[0].lower() == "!help" or content[0] == "@**goodbot**":
				if(len(content) == 1):
					self.client.send_message({
						"type": message_type,
						"topic": topic,
						"to": destination,
						"content": f"{greeting} :blush: Here's what I can do for you:\nType `!help gsod` for help with GSoD proposals.\nType `!help gsoc` for help with GSoC proposals.\nType `!help outreachy` for help with Outreachy proposals.\nType `!help faq 'your question'` to search FAQs.\nType `!help wikipedia 'title'` to search articles.\nType `!help stackoverflow 'your question'` to search questions.\nType `!help chat mediawiki` to get help regarding MediaWiki software.\nType `!help chat wikimedia` to get technical help regarding Wikimedia. You can also join the #**technical-support** channel to get technical help related to Wikimedia infrastructure."
					})
				elif(len(content) > 1):
					if content[1].lower() == "gsoc":
						self.subscribe_user("gsoc20-outreachy20", sender_email)
						self.client.send_message({
							"type": message_type,
							"topic": topic,
							"to": destination,
							"content": f"{greeting} Here are some links to get you started.\nRead the information guide for GSoC participants: https://www.mediawiki.org/wiki/Google_Summer_of_Code/Participants\nRead the project ideas for this year: https://www.mediawiki.org/wiki/Google_Summer_of_Code/2020\nYou have been subscribed to the #**gsoc20-outreachy20** stream for further help."
						})
					if content[1].lower() == "gsod":
						self.subscribe_user("gsod20", sender_email)
						self.client.send_message({
							"type": message_type,
							"topic": topic,
							"to": destination,
							"content": f"{greeting} Here are some links to get you started.\nRead the information guide for GSoD participants: https://www.mediawiki.org/wiki/Season_of_Docs/Participants\nRead the project ideas for this year: https://www.mediawiki.org/wiki/Season_of_Docs/2020\nYou have been subscribed to the #**gsod20** stream for further help."
						})
					if content[1].lower() == "outreachy":
						self.subscribe_user("gsoc20-outreachy20", sender_email)
						self.client.send_message({
							"type": message_type,
							"topic": topic,
							"to": destination,
							"content": f"{greeting} Here are some links to get you started.\nRead the information guide for Outreachy participants: https://www.mediawiki.org/wiki/Outreachy/Participants\nRead the project ideas for this year: https://www.mediawiki.org/wiki/Outreachy/Round_20\nYou have been subscribed to the #**gsoc20-outreachy20** stream for further help."
						})
					if content[1].lower() == "faq":
						if(len(content) == 2):
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
					if content[1].lower() == "wikipedia":
						if(len(content) == 2):
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
							"content": f"{greeting} This might take a while to process :time_ticking:"
						})
						query = " ".join(content[2:])
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
					if content[1].lower() == "stackoverflow":
						if(len(content) == 2):
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
							"content": f"{greeting} This might take a while to process :time_ticking:"
						})
						query = ' '.join(content[2:])
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
					if content[1].lower() == "chat":
						if(len(content) == 2):  # TODO: bunch all error control into one
							self.client.send_message({
								"type": message_type,
								"to": destination,
								"topic": topic,
								"content": f"{greeting} Please specify your required assistance in the following format:\n* `!help chat mediawiki` for assistance with MediaWiki software.\n* `!help chat wikimedia` for assistance with technical issues related to Wikimedia projects."
							})
							return
						if(content[2].lower() == "wikimedia"):
							self.subscribe_user("technical-support", sender_email)
							self.client.send_message({
								"type": message_type,
								"to": destination,
								"topic": topic,
								"content": f"{greeting} You can get help at the [#wikimedia-tech](https://webchat.freenode.net/?channels=wikimedia-tech) IRC channel or at [Wikimedia Developer Support](https://discourse-mediawiki.wmflabs.org) on Discourse.\nYou have been subscribed to the #**technical-support** stream for further help."
							})
						if(content[2].lower() == "mediawiki"):
							self.subscribe_user("technical-support", sender_email)
							self.client.send_message({
								"type": message_type,
								"to": destination,
								"topic": topic,
								"content": f"{greeting} You can get help at the [#mediawiki](https://webchat.freenode.net/?channels=mediawiki) IRC channel or at [Wikimedia Developer Support](https://discourse-mediawiki.wmflabs.org) on Discourse.\nYou can see a full list of available IRC channels [here](https://meta.wikimedia.org/wiki/IRC/Channels#MediaWiki_and_technical).\nYou have been subscribed to the #**technical-support** stream for further help."
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
