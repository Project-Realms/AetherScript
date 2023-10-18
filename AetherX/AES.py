from . import AESx64

def run():
	while True:
		text = input('<AetherScript> ')
		if text.strip() == "": continue
		result, error = AESx64.run('<stdin>', text)

		if error:
			print(error.as_string())
		elif result:
			if len(result.elements) == 1:
				print(repr(result.elements[0]))
			else:
				print(repr(result))

if __name__ == '__main__':
	run()
