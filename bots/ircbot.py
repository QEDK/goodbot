#!/usr/bin/env python3
import asyncio
import configparser
import functools
import irc.bot
import irc.strings
import itertools
import multiprocessing as mp
import os
import random
import re
import sched
import time
import zulip
from irc.bot import ReconnectStrategy
from irc.client import ip_numstr_to_quad, Event, ServerConnection
from irc.client_aio import AioReactor
from typing import Any, Dict


class IRCBot(irc.bot.SingleServerIRCBot):
	reactor_class = AioReactor

	class ExponentialBackoff(ReconnectStrategy):
		min_interval = 1
		max_interval = 1800

		def __init__(self, **attrs):
			vars(self).update(attrs)
			if not 0 <= self.min_interval <= self.max_interval:
				raise AssertionError
			self._check_scheduled = False
			self.attempt_count = itertools.count(1)

		def run(self, bot):
			self.bot = bot

			if self._check_scheduled:
				return

			interval = 2 ** next(self.attempt_count) - 1

			interval = min(interval, self.max_interval)

			interval = int(interval * random.random())

			interval = max(interval, self.min_interval)

			time.sleep(interval)
			self.check()
			self._check_scheduled = True

		def check(self):
			self._check_scheduled = False
			if not self.bot.connection.is_connected():
				self.run(self.bot)
				self.bot.connect()

	def __init__(self, config_file):
		# type: (Any, str) -> None
		config = configparser.ConfigParser()
		config.read(os.path.abspath(os.path.expanduser(config_file)))
		config = config["irc"]
		self.server = config.get("server")  # type: str
		self.port = config.getint("port", 6667)  # type: int
		self.nickname = config.get("nickname")  # type: str
		self.realname = config.get("realname", self.nickname)  # type: str
		self.min_interval = config.getint("min_interval", 1)  # type: int
		self.max_interval = config.getint("max_interval", 1800)  # type: int
		self.channel = config.get("channel")  # type: irc.bot.Channel
		self.password = config.get("nickserv_password")  # type: str
		self.stream = config.get("stream")  # type: str
		self.topic = config.get("topic", "IRC")  # type: str
		self.zulip_client = zulip.Client(config_file=config_file)
		irc.bot.SingleServerIRCBot.__init__(
			self, [(self.server, self.port)], self.nickname, self.realname,
			recon=self.ExponentialBackoff(min_interval=self.min_interval, max_interval=self.max_interval)
		)

	def connect(self, *args, **kwargs):
		# type: (*Any, **Any) -> None
		try:
			asyncio.get_event_loop().run_until_complete(self.connection.connect(self.server, self.port, self.nickname, password=self.password, **kwargs))
		except irc.client.ServerConnectionError as e:
			print(e)
			raise SystemExit(1)
		print("Connected to IRC server")

	def on_welcome(self, c, e):
		# type: (ServerConnection, Event) -> None
		c.join(self.channel)
		print("Joined IRC channel")

		def keepalive():
			s = sched.scheduler()
			s.enterabs(60, 0, functools.partial(self.connection.ping, "keep-alive"))
			s.run()

		proc = mp.Process(target=keepalive)
		proc.start()

		markdownfmt = re.compile(r"(_?\*\*|\|\d*\*\*|`{3,}\n)")
		replyfmt = re.compile(r"@.*\[said\].*```quote\n", flags=re.DOTALL)

		def forward_to_irc(msg):
			# type: (Dict[str, Any]) -> None
			if msg["sender_email"] == self.zulip_client.email:  # quick return
				return
			if msg["type"] == "stream":
				if msg["subject"].casefold() == self.topic.casefold() and msg["display_recipient"] == self.stream:
					msg["content"] = f"[zulip] <{msg['sender_full_name']}> {msg['content']}"
					dest = self.channel
				else:
					return
			else:
				recipients = [u["short_name"] for u in msg["display_recipient"] if u["email"] != msg["sender_email"]]
				if len(recipients) == 1:
					dest = recipients[0]
				else:
					dest = recipients
			msg["content"] = re.sub(replyfmt, "Quoting: ", msg["content"])
			msg["content"] = re.sub(markdownfmt, "", msg["content"])
			for line in msg["content"].split("\n"):
				c.privmsg(dest, line)

		proc = mp.Process(target=self.zulip_client.call_on_each_message, args=(forward_to_irc,))
		proc.start()
		if proc.is_alive():
			print("Connected to Zulip")

	def on_ctcp(self, c, e):
		# type: (ServerConnection, Event) -> None
		nick = e.source.nick
		if e.arguments[0] == "VERSION":
			c.ctcp_reply(nick, "VERSION " + self.get_version())
		elif e.arguments[0] == "PING":
			if len(e.arguments) > 1:
				c.ctcp_reply(nick, "PONG " + e.arguments[1])
		elif e.arguments[0] == "DCC" and e.arguments[1].split(" ", 1)[0] == "CHAT":
			self.on_dccchat(c, e)

	def on_privmsg(self, c, e):
		# type: (ServerConnection, Event) -> None
		content = e.arguments[0]
		sender = e.source.split("!")[0]

		# Forward the PM to Zulip
		print(self.zulip_client.send_message({
			"type": "stream",
			"to": self.stream,
			"topic": self.topic,
			"content": f"[irc] <{sender}> {content}"
		}))

	def on_pubmsg(self, c, e):
		# type: (ServerConnection, Event) -> None
		content = e.arguments[0]
		sender = e.source.split("!")[0]

		# Forward the stream message to Zulip
		print(self.zulip_client.send_message({
			"type": "stream",
			"to": self.stream,
			"topic": self.topic,
			"content": f"[irc] <{sender}> {content}"
		}))

	def on_dccmsg(self, c, e):
		# type: (ServerConnection, Event) -> None
		c.privmsg(f"You said: {e.arguments[0]}")

	def on_dccchat(self, c, e):
		# type: (ServerConnection, Event) -> None
		if len(e.arguments) != 2:
			return
		args = e.arguments[1].split()
		if len(args) == 4:
			try:
				address = ip_numstr_to_quad(args[2])
				port = int(args[3])
			except ValueError:
				return
			self.dcc_connect(address, port)


def main():
	print("Begin ircbot init")
	ircbot = IRCBot(config_file="~/ircbot")
	ircbot.start()


if __name__ == "__main__":
	main()
