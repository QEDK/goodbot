# goodbot
A chat(help)bot for Wikimedia Zulipchat.

## Style guidelines

Full list at https://www.flake8rules.com
Travis checks linting automatically for all commits.

### Ignored (should not be followed):

* **W191** ignored - Use tabs instead of spaces
* **E117** ignored - Over-indented allowed as a consequence of W191
* **E501** ignored - No line-length limit as chatbot responses are long

### Consequently (have to be followed):

* **E123** - closing bracket should match indentation of opening bracket's line
* **E126** - continuation line over-indented for hanging indent (one indent only)
* **W504** - line break after binary operator not allowed since E501 is ignored (no line-length limit)

