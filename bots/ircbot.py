#!/usr/bin/env python3
import zulip
import irc.bot
from irc.bot import ExponentialBackoff
import irc.strings
from irc.client import ip_numstr_to_quad, Event, ServerConnection
from irc.client_aio import AioReactor
import multiprocessing as mp
from typing import Any, Dict
import re
import sys
import os


class IRCBot(irc.bot.SingleServerIRCBot):
	reactor_class = AioReactor

	def __init__(self, zulip_client, stream, topic, channel, nickname, server, nickserv_password, port=6667):
		# type: (Any, str, str, irc.bot.Channel, str, str, str, int) -> None
		irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname, recon=ExponentialBackoff(min_interval=0))
		self.channel = channel  # type: irc.bot.Channel
		self.zulip_client = zulip_client
		self.stream = stream
		self.topic = topic
		self.IRC_DOMAIN = server
		self.nickserv_password = nickserv_password

	def connect(self, *args, **kwargs):
		# type: (*Any, **Any) -> None
		# https://github.com/jaraco/irc/blob/master/irc/client_aio.py
		try:
			self.reactor.loop.run_until_complete(self.connection.connect(*args, **kwargs))
		except irc.client.ServerConnectionError:
			print(sys.exc_info()[1])
			raise SystemExit(1)
		print("Connected to IRC server")

	def on_welcome(self, c, e):
		# type: (ServerConnection, Event) -> None
		msg = 'identify %s' % (self.nickserv_password)
		c.privmsg('NickServ', msg)
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
					msg["content"] = ("[zulip] <%s> " % msg["sender_full_name"]) + msg["content"]
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

	def on_privmsg(self, c, e):
		# type: (ServerConnection, Event) -> None
		content = e.arguments[0]
		sender = e.source.split("!")[0]

		# Forward the PM to Zulip
		print(self.zulip_client.send_message({
			"type": "stream",
			"to": self.stream,
			"topic": self.topic,
			"content": "[irc] <{0}> {1}".format(sender, content)
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
			"content": "[irc] <{0}> {1}".format(sender, content)
		}))

	def on_dccmsg(self, c, e):  # DCC<->Zulip compat not checked yet
		# type: (ServerConnection, Event) -> None
		c.privmsg("You said: " + e.arguments[0])

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
	ircbot = IRCBot(zulip.Client(config_file="~/ircbot"), "technical-support", "Testing", "#wikimedia-bots-testing", "zulipbridgebot", "irc.freenode.net", os.environ.get("IRC_PASSWORD"))
	ircbot.start()


if __name__ == "__main__":
	main()
