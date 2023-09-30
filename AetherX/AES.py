import Aesx64

while True:
	text = input('<AetherScript> ')
	if text.strip() == "": continue
	result, error = Aesx64.run('<stdin>', text)

	if error:
		print(error.as_string())
	elif result:
		if len(result.elements) == 1:
			print(repr(result.elements[0]))
		else:
			print(repr(result))
