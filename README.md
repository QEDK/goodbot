# goodbot [![Build Status](https://travis-ci.com/QEDK/goodbot.svg?branch=master)](https://travis-ci.com/QEDK/goodbot)
A chat(help)bot for Wikimedia Zulipchat.

## Directory guide
- **goodbot**
  - **bots**
    - **goodbot.py** Zulip chatbot
    - **ircbot.py** Zulip-IRC bridgebot

## Installation
It is recommended you use a virtual environment for building the project (such as Python's `venv` or the `virtualenv` module) to easily manage dependencies.
```bash
$ git clone git@github.com:QEDK/goodbot.git
$ cd goodbot
$ pip3 install -r requirements.txt
```

For running tests (you need to install flake8 and nose beforehand), run these commands inside the `goodbot` directory and it will automatically run the tests for you:
```bash
$ flake8 --ignore=W191,E117,E501 bots # linting, use --show-source to see individual errors
$ nosetests
```

## Style guidelines

Full list at https://www.flake8rules.com
Travis will check linting automatically for all commits (including pull requests), you can run flake8 with the required commands to get equivalent results.

### Ignored (should not be followed):

* **W191** ignored - Use tabs instead of spaces
* **E117** ignored - Over-indented allowed as a consequence of W191
* **E501** ignored - No line-length limit as chatbot responses are long

### Consequently (have to be followed):

* **E123** - closing bracket should match indentation of opening bracket's line
* **E126** - continuation line over-indented for hanging indent (one indent only)
* **W504** - line break after binary operator not allowed since E501 is ignored (no line-length limit)

