#!/usr/bin/env python3
import zulip
import irc.bot
from irc.bot import ExponentialBackoff
import irc.strings
from irc.client import ip_numstr_to_quad, Event, ServerConnection
from irc.client_aio import AioReactor
import multiprocessing as mp
from typing import Any, Dict
import configparser
import re
import os
import asyncio


class IRCBot(irc.bot.SingleServerIRCBot):
	reactor_class = AioReactor

	def __init__(self, config_file):
		# type: (Any, str) -> None
		config = configparser.ConfigParser()
		config.read(os.path.abspath(os.path.expanduser(config_file)))
		config = config["irc"]
		self.server = config.get("server")  # type: str
		self.port = config.getint("port", 6667)  # type: int
		self.nickname = config.get("nickname")  # type: str
		self.realname = config.get("realname", self.nickname)  # type: str
		self.min_interval = config.getint("min_interval", 0)  # type: int
		self.channel = config.get("channel")  # type: irc.bot.Channel
		self.password = config.get("nickserv_password")  # type: str
		self.stream = config.get("stream")  # type: str
		self.topic = config.get("topic", "IRC")  # type: str
		self.zulip_client = zulip.Client(config_file=config_file)
		irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port)], self.nickname, self.realname, recon=ExponentialBackoff(min_interval=self.min_interval))

	def connect(self, *args, **kwargs):
		# type: (*Any, **Any) -> None
		# https://github.com/jaraco/irc/blob/master/irc/client_aio.py
		try:
			self.reactor.loop.run_until_complete(self.connection.connect(self.server, self.port, self.nickname, password=self.password, **kwargs))
		except irc.client.ServerConnectionError as e:
			print(e)
			raise SystemExit(1)
		print("Connected to IRC server")

	def on_welcome(self, c, e):
		# type: (ServerConnection, Event) -> None
		c.join(self.channel)
		print("Joined IRC channel")

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

	async def on_privmsg(self, c, e):
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

	async def on_pubmsg(self, c, e):
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

	async def on_dccmsg(self, c, e):  # DCC<->Zulip compat not checked yet
		# type: (ServerConnection, Event) -> None
		c.privmsg(f"You said: {e.arguments[0]}")

	async def on_dccchat(self, c, e):
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
	asyncio.run(ircbot.start())


if __name__ == "__main__":
	main()
