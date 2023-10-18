class AetherScriptError:
	def call(self, *args: object):
		return SyntaxError(*args)
