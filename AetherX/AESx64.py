from .functions import string_with_arrows
from .errors import AetherScriptError

import string
import os
import math

Constants = '0123456789'
LETTERS = string.ascii_letters
LETTERS_DIGITS = LETTERS + Constants

class Error:
	def __init__(self, pos_start, pos_end, error_name, details):
		self.pos_start = pos_start
		self.pos_end = pos_end
		self.error_name = error_name
		self.details = details

	def as_string(self):
		result  = f'{self.error_name}: {self.details}\n'
		result += f'File {self.pos_start.fn}, line {self.pos_start.ln + 1}'
		result += '\n\n' + string_with_arrows(self.pos_start.ftxt, self.pos_start, self.pos_end)
		return result

class IllegalCharError(Error):
	def __init__(self, pos_start, pos_end, details):
		super().__init__(pos_start, pos_end, 'Forbidden Character Found', details)

class ExpectedCharError(Error):
	def __init__(self, pos_start, pos_end, details):
		super().__init__(pos_start, pos_end, 'Expected Character', details)

class InvalidSyntaxError(Error):
	def __init__(self, pos_start, pos_end, details=''):
		super().__init__(pos_start, pos_end, 'Invalid Structure', details)

class RTError(Error):
	def __init__(self, pos_start, pos_end, details, context):
		super().__init__(pos_start, pos_end, 'Runtime Error', details)
		self.context = context

	def as_string(self):
		result  = self.generate_traceback()
		result += f'{self.error_name}: {self.details}'
		result += '\n\n' + string_with_arrows(self.pos_start.ftxt, self.pos_start, self.pos_end)
		return result

	def generate_traceback(self):
		result = ''
		pos = self.pos_start
		ctx = self.context

		while ctx:
			result = f'  File {pos.fn}, line {str(pos.ln + 1)}, in {ctx.display_name}\n{result}'
			pos = ctx.parent_entry_pos
			ctx = ctx.parent

		return 'Traceback: \n' + result

class Coordinates:
	def __init__(self, idx, ln, col, fn, ftxt):
		self.idx = idx
		self.ln = ln
		self.col = col
		self.fn = fn
		self.ftxt = ftxt

	def advance(self, current_char=None):
		self.idx += 1
		self.col += 1

		if current_char == '\n':
			self.ln += 1
			self.col = 0

		return self

	def copy(self):
		return Coordinates(self.idx, self.ln, self.col, self.fn, self.ftxt)

# tokens

ttint				= 'Integer'
ttfloat    	= 'Float'
ttstring			= 'String'
ttidentifier	= 'Identifier'
ttkeyword		= 'Keyword'
ttaddition     	= 'Addition'
ttsubstraction    	= 'Substraction'
ttmultiplication      	= 'Multiplication'
ttdivision     	= 'Division'
ttpower				= 'Power'
tteq					= 'EQ'
ttleftparenthesis  	= 'Left Parenthesis'
ttrightparenthesis   	= 'Right Parenthesis'
ttleftsqbr    = 'LeftSquare BR'
ttrightsqbr    = 'RightSquare BR'
ttee					= 'EE'
ttne					= 'NE'
ttlt					= 'LT'
ttgt					= 'GT'
ttlte				= 'LTE'
ttgte				= 'GTE'
ttcomma			= 'Comma'
ttarrow			= 'Arrow'
ttnewline		= 'Newline'
tteof				= 'EOF'

# keywords

KEYWORDS = [
	'Var',
	'And',
	'Or',
	'Not',
	'If',
	'Elif',
	'Else',
	'For',
	'To',
	'Step',
	'While',
	'Function',
	'Then',
	'End',
	'Return',
	'Continue',
	'Break',
]

class Token:
	def __init__(self, type_, value=None, pos_start=None, pos_end=None):
		self.type = type_
		self.value = value

		if pos_start:
			self.pos_start = pos_start.copy()
			self.pos_end = pos_start.copy()
			self.pos_end.advance()

		if pos_end:
			self.pos_end = pos_end.copy()

	def matches(self, type_, value):
		return self.type == type_ and self.value == value

	def __repr__(self):
		return f'{self.type}:{self.value}' if self.value else f'{self.type}'

# Lexer

class Lexer:
	def __init__(self, fn, text):
		self.fn = fn
		self.text = text
		self.pos = Coordinates(-1, 0, -1, fn, text)
		self.current_char = None
		self.advance()

	def advance(self):
		self.pos.advance(self.current_char)
		self.current_char = self.text[self.pos.idx] if self.pos.idx < len(self.text) else None

	def make_tokens(self):
		tokens = []

		while self.current_char != None:
			char_met = False
			for chars, funcs in {
				' \t': [self.advance()],
				'~': [self.skip_comment()],
				';\n': [tokens.append(Token(ttnewline, pos_start=self.pos)), self.advance()],
				Constants: [tokens.append(self.make_number())],
				LETTERS: [tokens.append(self.make_identifier())],
				'"': [tokens.append(self.make_string())],
				'+': [tokens.append(Token(ttaddition, pos_start=self.pos)), self.advance()],
				'-': [tokens.append(self.make_minus_or_arrow())],
				'*': [tokens.append(Token(ttmultiplication, pos_start=self.pos)), self.advance()],
				'/': [tokens.append(Token(ttdivision, pos_start=self.pos)), self.advance()],
				'^': [tokens.append(Token(ttpower, pos_start=self.pos)), self.advance()],
				'(': [tokens.append(Token(ttleftparenthesis, pos_start=self.pos)), self.advance()],
				')': [tokens.append(Token(ttrightparenthesis, pos_start=self.pos)), self.advance()],
				'[': [tokens.append(Token(ttleftsqbr, pos_start=self.pos)), self.advance()],
				']': [tokens.append(Token(ttrightsqbr, pos_start=self.pos)), self.advance()],
				'!': [],
				'=': [tokens.append(self.make_equals())],
				'<': [tokens.append(self.make_less_than())],
				'>': [tokens.append(self.make_greater_than())],
				',': [tokens.append(Token(ttcomma, pos_start=self.pos)), self.advance()],
			}.items():
				if self.current_char in chars:
					char_met = True
					if self.current_char in '!':
						token, error = self.make_not_equals()
						if error: return [], error
						tokens.append(token)
					for func in funcs:
						func()
			if char_met:
				pos_start = self.pos.copy()
				char_out = self.current_char
				self.advance()
				return [], IllegalCharError(pos_start, self.pos, f"'{char_out}'")

		tokens.append(Token(tteof, pos_start=self.pos))
		return tokens, None

	def make_number(self):
		num_str = ''
		dot_count = 0
		pos_start = self.pos.copy()

		while self.current_char != None and self.current_char in f'{Constants}.':
			if self.current_char == '.':
				if dot_count == 1: break
				dot_count += 1
			num_str += self.current_char
			self.advance()

		if dot_count == 0:
			return Token(ttint, int(num_str), pos_start, self.pos)
		else:
			return Token(ttfloat, float(num_str), pos_start, self.pos)

	def make_string(self):
		string = ''
		pos_start = self.pos.copy()
		escape_character = False
		self.advance()

		escape_characters = {
			'n': '\n',
			't': '\t'
		}

		while self.current_char != None and (self.current_char != '"' or escape_character):
			if escape_character:
				string += escape_characters.get(self.current_char, self.current_char)
			elif self.current_char == '\\':
				escape_character = True
			else:
				string += self.current_char
			self.advance()
			escape_character = False

		self.advance()
		return Token(ttstring, string, pos_start, self.pos)

	def make_identifier(self):
		id_str = ''
		pos_start = self.pos.copy()

		while self.current_char != None and self.current_char in f'{LETTERS_DIGITS}_':
			id_str += self.current_char
			self.advance()

		tok_type = ttkeyword if id_str in KEYWORDS else ttidentifier
		return Token(tok_type, id_str, pos_start, self.pos)

	def make_minus_or_arrow(self):
		tok_type = ttsubstraction
		pos_start = self.pos.copy()
		self.advance()

		if self.current_char == '>':
			self.advance()
			tok_type = ttarrow

		return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

	def make_not_equals(self):
		pos_start = self.pos.copy()
		self.advance()

		if self.current_char == '=':
			self.advance()
			return Token(ttne, pos_start=pos_start, pos_end=self.pos), None

		self.advance()
		return None, ExpectedCharError(pos_start, self.pos, "'=' (after '!')")

	def make_equals(self):
		tok_type = tteq
		pos_start = self.pos.copy()
		self.advance()

		if self.current_char == '=':
			self.advance()
			tok_type = ttee

		return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

	def make_less_than(self):
		tok_type = ttlt
		pos_start = self.pos.copy()
		self.advance()

		if self.current_char == '=':
			self.advance()
			tok_type = ttlte

		return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

	def make_greater_than(self):
		tok_type = ttgt
		pos_start = self.pos.copy()
		self.advance()

		if self.current_char == '=':
			self.advance()
			tok_type = ttgte

		return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

	def skip_comment(self):
		self.advance()

		while self.current_char != '\n':
			self.advance()

		self.advance()

# nodes

class number_node:
	def __init__(self, tok):
		self.tok = tok

		self.pos_start = self.tok.pos_start
		self.pos_end = self.tok.pos_end

	def __repr__(self):
		return f'{self.tok}'

class string_node:
	def __init__(self, tok):
		self.tok = tok

		self.pos_start = self.tok.pos_start
		self.pos_end = self.tok.pos_end

	def __repr__(self):
		return f'{self.tok}'

class list_node:
	def __init__(self, element_nodes, pos_start, pos_end):
		self.element_nodes = element_nodes

		self.pos_start = pos_start
		self.pos_end = pos_end

class var_access_node:
	def __init__(self, var_name_tok):
		self.var_name_tok = var_name_tok

		self.pos_start = self.var_name_tok.pos_start
		self.pos_end = self.var_name_tok.pos_end

class var_assign_node:
	def __init__(self, var_name_tok, value_node):
		self.var_name_tok = var_name_tok
		self.value_node = value_node

		self.pos_start = self.var_name_tok.pos_start
		self.pos_end = self.value_node.pos_end

class bin_op_node:
	def __init__(self, left_node, op_tok, right_node):
		self.left_node = left_node
		self.op_tok = op_tok
		self.right_node = right_node

		self.pos_start = self.left_node.pos_start
		self.pos_end = self.right_node.pos_end

	def __repr__(self):
		return f'({self.left_node}, {self.op_tok}, {self.right_node})'

class unary_op_node:
	def __init__(self, op_tok, node):
		self.op_tok = op_tok
		self.node = node

		self.pos_start = self.op_tok.pos_start
		self.pos_end = node.pos_end

	def __repr__(self):
		return f'({self.op_tok}, {self.node})'

class if_node:
	def __init__(self, cases, else_case):
		self.cases = cases
		self.else_case = else_case

		self.pos_start = self.cases[0][0].pos_start
		self.pos_end = (self.else_case or self.cases[len(self.cases) - 1])[0].pos_end

class for_node:
	def __init__(self, var_name_tok, start_value_node, end_value_node, step_value_node, body_node, should_return_null):
		self.var_name_tok = var_name_tok
		self.start_value_node = start_value_node
		self.end_value_node = end_value_node
		self.step_value_node = step_value_node
		self.body_node = body_node
		self.should_return_null = should_return_null

		self.pos_start = self.var_name_tok.pos_start
		self.pos_end = self.body_node.pos_end

class while_node:
	def __init__(self, condition_node, body_node, should_return_null):
		self.condition_node = condition_node
		self.body_node = body_node
		self.should_return_null = should_return_null

		self.pos_start = self.condition_node.pos_start
		self.pos_end = self.body_node.pos_end

class func_def_node:
	def __init__(self, var_name_tok, arg_name_toks, body_node, should_auto_return):
		self.var_name_tok = var_name_tok
		self.arg_name_toks = arg_name_toks
		self.body_node = body_node
		self.should_auto_return = should_auto_return

		if self.var_name_tok:
			self.pos_start = self.var_name_tok.pos_start
		elif len(self.arg_name_toks) > 0:
			self.pos_start = self.arg_name_toks[0].pos_start
		else:
			self.pos_start = self.body_node.pos_start

		self.pos_end = self.body_node.pos_end

class call_node:
	def __init__(self, node_to_call, arg_nodes):
		self.node_to_call = node_to_call
		self.arg_nodes = arg_nodes

		self.pos_start = self.node_to_call.pos_start

		if len(self.arg_nodes) > 0:
			self.pos_end = self.arg_nodes[len(self.arg_nodes) - 1].pos_end
		else:
			self.pos_end = self.node_to_call.pos_end

class return_node:
	def __init__(self, node_to_return, pos_start, pos_end):
		self.node_to_return = node_to_return

		self.pos_start = pos_start
		self.pos_end = pos_end

class continue_node:
	def __init__(self, pos_start, pos_end):
		self.pos_start = pos_start
		self.pos_end = pos_end

class break_node:
	def __init__(self, pos_start, pos_end):
		self.pos_start = pos_start
		self.pos_end = pos_end

# ParseResult

class ParseResult:
	def __init__(self):
		self.error = None
		self.node = None
		self.last_registered_advance_count = 0
		self.advance_count = 0
		self.to_reverse_count = 0

	def register_advancement(self):
		self.last_registered_advance_count = 1
		self.advance_count += 1

	def register(self, res):
		self.last_registered_advance_count = res.advance_count
		self.advance_count += res.advance_count
		if res.error: self.error = res.error
		return res.node

	def try_register(self, res):
		if res.error:
			self.to_reverse_count = res.advance_count
			return None
		return self.register(res)

	def success(self, node):
		self.node = node
		return self

	def failure(self, error):
		if not self.error or self.last_registered_advance_count == 0:
			self.error = error
		return self

# Parser

class Parser:
	def __init__(self, tokens):
		self.tokens = tokens
		self.tok_idx = -1
		self.advance()

	def advance(self):
		self.tok_idx += 1
		self.update_current_tok()
		return self.current_tok

	def reverse(self, amount=1):
		self.tok_idx -= amount
		self.update_current_tok()
		return self.current_tok

	def update_current_tok(self):
		if self.tok_idx >= 0 and self.tok_idx < len(self.tokens):
			self.current_tok = self.tokens[self.tok_idx]

	def parse(self):
		res = self.statements()
		if not res.error and self.current_tok.type != tteof:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Token cannot appear after previous tokens! Please do Revise the Code."
			))
		return res

	def statements(self):
		res = ParseResult()
		pos_start = self.current_tok.pos_start.copy()

		while self.current_tok.type == ttnewline:
			res.register_advancement()
			self.advance()

		statement = res.register(self.statement())
		if res.error: return res
		statements = [statement]
		more_statements = True

		while True:
			newline_count = 0
			while self.current_tok.type == ttnewline:
				res.register_advancement()
				self.advance()
				newline_count += 1
			if newline_count == 0:
				more_statements = False

			if not more_statements: break
			statement = res.try_register(self.statement())
			if not statement:
				self.reverse(res.to_reverse_count)
				more_statements = False
				continue
			statements.append(statement)

		return res.success(list_node(
			statements,
			pos_start,
			self.current_tok.pos_end.copy()
		))

	def statement(self):
		res = ParseResult()
		pos_start = self.current_tok.pos_start.copy()

		if self.current_tok.matches(ttkeyword, 'Return'):
			res.register_advancement()
			self.advance()

			expr = res.try_register(self.expr())
			if not expr:
				self.reverse(res.to_reverse_count)
			return res.success(return_node(expr, pos_start, self.current_tok.pos_start.copy()))
		
		if self.current_tok.matches(ttkeyword, 'Continue'):
			res.register_advancement()
			self.advance()
			return res.success(continue_node(pos_start, self.current_tok.pos_start.copy()))
			
		if self.current_tok.matches(ttkeyword, 'Break'):
			res.register_advancement()
			self.advance()
			return res.success(break_node(pos_start, self.current_tok.pos_start.copy()))

		expr = res.register(self.expr())
		if res.error:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'Return', 'Continue', 'Break', 'Variable', 'If', 'For', 'While', 'Function', int, float, identifier, '+', '-', '(', '[' or 'Not'"
			))
		return res.success(expr)

	def expr(self):
		res = ParseResult()

		if self.current_tok.matches(ttkeyword, 'Variable'):
			return self.advance_res(res)
		node = res.register(self.bin_op(self.comp_expr, ((ttkeyword, 'And'), (ttkeyword, 'Or'))))

		if res.error:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'Variable', 'If', 'For', 'While', 'Function', int, float, identifier, '+', '-', '(', '[' or 'Not'"
			))

		return res.success(node)

	def advance_res(self, res):
		res.register_advancement()
		self.advance()

		if self.current_tok.type != ttidentifier:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: identifier"
			))

		var_name = self.current_tok
		res.register_advancement()
		self.advance()

		if self.current_tok.type != tteq:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: '='"
			))

		res.register_advancement()
		self.advance()
		expr = res.register(self.expr())
		return res if res.error else res.success(var_assign_node(var_name, expr))

	def comp_expr(self):
		res = ParseResult()

		if self.current_tok.matches(ttkeyword, 'Not'):
			return self.advance_register(res)
		node = res.register(self.bin_op(self.arith_expr, (ttee, ttne, ttlt, ttgt, ttlte, ttgte)))

		if res.error:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: int, float, identifier, '+', '-', '(', '[', 'If', 'For', 'While', 'Function' or 'Not'"
			))

		return res.success(node)

	def advance_register(self, res):
		op_tok = self.current_tok
		res.register_advancement()
		self.advance()

		node = res.register(self.comp_expr())
		return res if res.error else res.success(unary_op_node(op_tok, node))

	def arith_expr(self):
		return self.bin_op(self.term, (ttaddition, ttsubstraction))

	def term(self):
		return self.bin_op(self.factor, (ttmultiplication, ttdivision))

	def factor(self):
		res = ParseResult()
		tok = self.current_tok

		if tok.type in (ttaddition, ttsubstraction):
			res.register_advancement()
			self.advance()
			factor = res.register(self.factor())
			return res if res.error else res.success(unary_op_node(tok, factor))
		return self.power()

	def power(self):
		return self.bin_op(self.call, (ttpower, ), self.factor)

	def call(self):
		res = ParseResult()
		atom = res.register(self.atom())
		if res.error: return res

		if self.current_tok.type == ttleftparenthesis:
			return self.advance_registry(res, atom)
		return res.success(atom)

	def advance_registry(self, res, atom):
		res.register_advancement()
		self.advance()
		arg_nodes = []

		if self.current_tok.type != ttrightparenthesis:
			arg_nodes.append(res.register(self.expr()))
			if res.error:
				return res.failure(InvalidSyntaxError(
					self.current_tok.pos_start, self.current_tok.pos_end,
					"Expected Character: ')', 'Variable', 'If', 'For', 'While', 'Function', int, float, identifier, '+', '-', '(', '[' or 'Not'"
				))

			while self.current_tok.type == ttcomma:
				res.register_advancement()
				self.advance()

				arg_nodes.append(res.register(self.expr()))
				if res.error: return res

		if self.current_tok.type != ttrightparenthesis:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: ',' or ')'"
			))

		res.register_advancement()
		self.advance()
		return res.success(call_node(atom, arg_nodes))

	def atom(self):
		res = ParseResult()
		tok = self.current_tok

		if tok.type in (ttint, ttfloat):
			res.register_advancement()
			self.advance()
			return res.success(number_node(tok))

		elif tok.type == ttstring:
			res.register_advancement()
			self.advance()
			return res.success(string_node(tok))

		elif tok.type == ttidentifier:
			res.register_advancement()
			self.advance()
			return res.success(var_access_node(tok))

		elif tok.type == ttleftparenthesis:
			return self.advance_registry(res)
		elif tok.type == ttleftsqbr:
			list_expr = res.register(self.list_expr())
			return res if res.error else res.success(list_expr)
		elif tok.matches(ttkeyword, 'If'):
			if_expr = res.register(self.if_expr())
			return res if res.error else res.success(if_expr)
		elif tok.matches(ttkeyword, 'For'):
			for_expr = res.register(self.for_expr())
			return res if res.error else res.success(for_expr)
		elif tok.matches(ttkeyword, 'While'):
			while_expr = res.register(self.while_expr())
			return res if res.error else res.success(while_expr)
		elif tok.matches(ttkeyword, 'Function'):
			func_def = res.register(self.func_def())
			return res if res.error else res.success(func_def)
		return res.failure(InvalidSyntaxError(
			tok.pos_start, tok.pos_end,
			"Expected Character: int, float, identifier, '+', '-', '(', '[', If', 'For', 'While', 'Function'"
		))

	def advance_registry(self, res):
		res.register_advancement()
		self.advance()
		expr = res.register(self.expr())
		if res.error: return res
		if self.current_tok.type != ttrightparenthesis:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: ')'"
			))

		res.register_advancement()
		self.advance()
		return res.success(expr)

	def list_expr(self):
		res = ParseResult()
		element_nodes = []
		pos_start = self.current_tok.pos_start.copy()

		if self.current_tok.type != ttleftsqbr:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: '['"
			))

		res.register_advancement()
		self.advance()

		if self.current_tok.type != ttrightsqbr:
			element_nodes.append(res.register(self.expr()))
			if res.error:
				return res.failure(InvalidSyntaxError(
					self.current_tok.pos_start, self.current_tok.pos_end,
					"Expected Character: ']', 'Variable', 'If', 'For, 'While', 'Function', int, float, identifier, '+', '-', '(', '[' or 'Not'"
				))

			while self.current_tok.type == ttcomma:
				res.register_advancement()
				self.advance()

				element_nodes.append(res.register(self.expr()))
				if res.error: return res

		if self.current_tok.type != ttrightsqbr:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: ',' or ']'"
			))

		res.register_advancement()
		self.advance()
		return res.success(list_node(
			element_nodes,
			pos_start,
			self.current_tok.pos_end.copy()
		))

	def if_expr(self):
		res = ParseResult()
		all_cases = res.register(self.if_expr_cases('If'))
		if res.error: return res
		cases, else_case = all_cases
		return res.success(if_node(cases, else_case))

	def if_expr_b(self):
		return self.if_expr_cases('Elif')
		
	def if_expr_c(self):
		res = ParseResult()
		else_case = None

		if self.current_tok.matches(ttkeyword, 'Else'):
			res.register_advancement()
			self.advance()

			if self.current_tok.type == ttnewline:
				res.register_advancement()
				self.advance()

				statements = res.register(self.statements())
				if res.error: return res
				else_case = (statements, True)

				if not self.current_tok.matches(ttkeyword, 'End'):
					return res.failure(InvalidSyntaxError(
						self.current_tok.pos_start, self.current_tok.pos_end,
						"Expected Character: 'End'"
					))
				res.register_advancement()
				self.advance()
			else:
				expr = res.register(self.statement())
				if res.error: return res
				else_case = (expr, False)

		return res.success(else_case)

	def if_expr_b_or_c(self):
		res = ParseResult()
		cases, else_case = [], None

		if self.current_tok.matches(ttkeyword, 'Elif'):
			all_cases = res.register(self.if_expr_b())
			if res.error: return res
			cases, else_case = all_cases
		else:
			else_case = res.register(self.if_expr_c())
			if res.error: return res
		
		return res.success((cases, else_case))

	def if_expr_cases(self, case_keyword):
		res = ParseResult()
		cases = []
		else_case = None

		if not self.current_tok.matches(ttkeyword, case_keyword):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				f"Expected Character: '{case_keyword}'"
			))

		res.register_advancement()
		self.advance()

		condition = res.register(self.expr())
		if res.error: return res

		if not self.current_tok.matches(ttkeyword, 'Then'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'Then'"
			))

		res.register_advancement()
		self.advance()

		if self.current_tok.type == ttnewline:
			res.register_advancement()
			self.advance()

			statements = res.register(self.statements())
			if res.error: return res
			cases.append((condition, statements, True))

			if self.current_tok.matches(ttkeyword, 'End'):
				res.register_advancement()
				self.advance()
			else:
				all_cases = res.register(self.if_expr_b_or_c())
				if res.error: return res
				new_cases, else_case = all_cases
				cases.extend(new_cases)
		else:
			expr = res.register(self.statement())
			if res.error: return res
			cases.append((condition, expr, False))

			all_cases = res.register(self.if_expr_b_or_c())
			if res.error: return res
			new_cases, else_case = all_cases
			cases.extend(new_cases)

		return res.success((cases, else_case))

	def for_expr(self):
		res = ParseResult()

		if not self.current_tok.matches(ttkeyword, 'For'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character:'For'"
			))

		res.register_advancement()
		self.advance()

		if self.current_tok.type != ttidentifier:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: identifier"
			))

		var_name = self.current_tok
		res.register_advancement()
		self.advance()

		if self.current_tok.type != tteq:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: '='"
			))
		
		res.register_advancement()
		self.advance()

		start_value = res.register(self.expr())
		if res.error: return res

		if not self.current_tok.matches(ttkeyword, 'To'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'To'"
			))
		
		res.register_advancement()
		self.advance()

		end_value = res.register(self.expr())
		if res.error: return res

		if self.current_tok.matches(ttkeyword, 'Step'):
			res.register_advancement()
			self.advance()

			step_value = res.register(self.expr())
			if res.error: return res
		else:
			step_value = None

		if not self.current_tok.matches(ttkeyword, 'Then'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'Then'"
			))

		res.register_advancement()
		self.advance()

		if self.current_tok.type == ttnewline:
			res.register_advancement()
			self.advance()

			body = res.register(self.statements())
			if res.error: return res

			if not self.current_tok.matches(ttkeyword, 'End'):
				return res.failure(InvalidSyntaxError(
					self.current_tok.pos_start, self.current_tok.pos_end,
					"Expected Character: 'End'"
				))

			res.register_advancement()
			self.advance()

			return res.success(for_node(var_name, start_value, end_value, step_value, body, True))
		
		body = res.register(self.statement())
		if res.error: return res

		return res.success(for_node(var_name, start_value, end_value, step_value, body, False))

	def while_expr(self):
		res = ParseResult()

		if not self.current_tok.matches(ttkeyword, 'While'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'While'"
			))

		res.register_advancement()
		self.advance()

		condition = res.register(self.expr())
		if res.error: return res

		if not self.current_tok.matches(ttkeyword, 'Then'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'Then'"
			))

		res.register_advancement()
		self.advance()

		if self.current_tok.type == ttnewline:
			return self.advance_register(res, condition)
		body = res.register(self.statement())
		return res if res.error else res.success(while_node(condition, body, False))

	def advance_register(self, res, condition):
		res.register_advancement()
		self.advance()

		body = res.register(self.statements())
		if res.error: return res

		if not self.current_tok.matches(ttkeyword, 'End'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'End'"
			))

		res.register_advancement()
		self.advance()

		return res.success(while_node(condition, body, True))

	def func_def(self):
		res = ParseResult()

		if not self.current_tok.matches(ttkeyword, 'Function'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'Function'"
			))

		res.register_advancement()
		self.advance()

		if self.current_tok.type == ttidentifier:
			var_name_tok = self.current_tok
			res.register_advancement()
			self.advance()
			if self.current_tok.type != ttleftparenthesis:
				return res.failure(InvalidSyntaxError(
					self.current_tok.pos_start, self.current_tok.pos_end,
					"Expected Character: '('"
				))
		else:
			var_name_tok = None
			if self.current_tok.type != ttleftparenthesis:
				return res.failure(InvalidSyntaxError(
					self.current_tok.pos_start, self.current_tok.pos_end,
					"Expected Character: identifier or '('"
				))

		res.register_advancement()
		self.advance()
		arg_name_toks = []

		if self.current_tok.type == ttidentifier:
			self.advance_registry(arg_name_toks, res)
			while self.current_tok.type == ttcomma:
				res.register_advancement()
				self.advance()

				if self.current_tok.type == ttidentifier:
					self.advance_registry(arg_name_toks, res)
				else:
					return res.failure(InvalidSyntaxError(
						self.current_tok.pos_start, self.current_tok.pos_end,
						"Expected Character: identifier"
					))

			if self.current_tok.type != ttrightparenthesis:
				return res.failure(InvalidSyntaxError(
					self.current_tok.pos_start, self.current_tok.pos_end,
					"Expected Character: ',' or ')'"
				))
		elif self.current_tok.type != ttrightparenthesis:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: identifier or ')'"
			))

		res.register_advancement()
		self.advance()

		if self.current_tok.type == ttarrow:
			res.register_advancement()
			self.advance()

			body = res.register(self.expr())
			if res.error: return res

			return res.success(func_def_node(
				var_name_tok,
				arg_name_toks,
				body,
				True
			))

		if self.current_tok.type != ttnewline:
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: '->' or Newline"
			))

		res.register_advancement()
		self.advance()

		body = res.register(self.statements())
		if res.error: return res

		if not self.current_tok.matches(ttkeyword, 'End'):
			return res.failure(InvalidSyntaxError(
				self.current_tok.pos_start, self.current_tok.pos_end,
				"Expected Character: 'End'"
			))

		res.register_advancement()
		self.advance()

		return res.success(func_def_node(
			var_name_tok,
			arg_name_toks,
			body,
			False
		))

	def advance_registry(self, arg_name_toks, res):
		arg_name_toks.append(self.current_tok)
		res.register_advancement()
		self.advance()

	def bin_op(self, func_a, ops, func_b=None):
		if func_b is None:
			func_b = func_a
		
		res = ParseResult()
		left = res.register(func_a())
		if res.error: return res

		while self.current_tok.type in ops or (self.current_tok.type, self.current_tok.value) in ops:
			op_tok = self.current_tok
			res.register_advancement()
			self.advance()
			right = res.register(func_b())
			if res.error: return res
			left = bin_op_node(left, op_tok, right)

		return res.success(left)

# runtime result

class RTResult:
	def __init__(self):
		self.reset()

	def reset(self):
		self.value = None
		self.error = None
		self.func_return_value = None
		self.loop_should_continue = False
		self.loop_should_break = False

	def register(self, res):
		self.error = res.error
		self.func_return_value = res.func_return_value
		self.loop_should_continue = res.loop_should_continue
		self.loop_should_break = res.loop_should_break
		return res.value

	def success(self, value):
		self.reset()
		self.value = value
		return self

	def success_return(self, value):
		self.reset()
		self.func_return_value = value
		return self

	def success_continue(self):
		self.reset()
		self.loop_should_continue = True
		return self

	def success_break(self):
		self.reset()
		self.loop_should_break = True
		return self

	def failure(self, error):
		self.reset()
		self.error = error
		return self

	def should_return(self):
		return (
			self.error or
			self.func_return_value or
			self.loop_should_continue or
			self.loop_should_break
		)

# values

class Value:
	def __init__(self):
		self.set_pos()
		self.set_context()

	def set_pos(self, pos_start=None, pos_end=None):
		self.pos_start = pos_start
		self.pos_end = pos_end
		return self

	def set_context(self, context=None):
		self.context = context
		return self

	def added_to(self, other):
		return None, self.illegal_operation(other)

	def subbed_by(self, other):
		return None, self.illegal_operation(other)

	def multed_by(self, other):
		return None, self.illegal_operation(other)

	def dived_by(self, other):
		return None, self.illegal_operation(other)

	def powed_by(self, other):
		return None, self.illegal_operation(other)

	def get_comparison_eq(self, other):
		return None, self.illegal_operation(other)

	def get_comparison_ne(self, other):
		return None, self.illegal_operation(other)

	def get_comparison_lt(self, other):
		return None, self.illegal_operation(other)

	def get_comparison_gt(self, other):
		return None, self.illegal_operation(other)

	def get_comparison_lte(self, other):
		return None, self.illegal_operation(other)

	def get_comparison_gte(self, other):
		return None, self.illegal_operation(other)

	def anded_by(self, other):
		return None, self.illegal_operation(other)

	def ored_by(self, other):
		return None, self.illegal_operation(other)

	def notted(self, other=None):
		return None, self.illegal_operation(other)

	def execute(self):
		return RTResult().failure(self.illegal_operation())

	def copy(self):
		raise AetherScriptError.call('No copy method defined.')

	def is_true(self):
		return False

	def illegal_operation(self, other=None):
		if not other: other = self
		return RTError(
			self.pos_start, other.pos_end,
			'Illegal operation!',
			self.context
		)

class Number(Value):
	def __init__(self, value):
		super().__init__()
		self.value = value

	def added_to(self, other):
		if isinstance(other, Number):
			return Number(self.value + other.value).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def subbed_by(self, other):
		if isinstance(other, Number):
			return Number(self.value - other.value).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def multed_by(self, other):
		if isinstance(other, Number):
			return Number(self.value * other.value).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def dived_by(self, other):
		if not isinstance(other, Number):
			return None, Value.illegal_operation(self, other)
		if other.value == 0:
			return None, RTError(
				other.pos_start, other.pos_end,
				'Division by zero? What are you trying?',
				self.context
			)

		return Number(self.value / other.value).set_context(self.context), None

	def powed_by(self, other):
		if isinstance(other, Number):
			return Number(self.value ** other.value).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def get_comparison_eq(self, other):
		if isinstance(other, Number):
			return Number(int(self.value == other.value)).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def get_comparison_ne(self, other):
		if isinstance(other, Number):
			return Number(int(self.value != other.value)).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def get_comparison_lt(self, other):
		if isinstance(other, Number):
			return Number(int(self.value < other.value)).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def get_comparison_gt(self, other):
		if isinstance(other, Number):
			return Number(int(self.value > other.value)).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def get_comparison_lte(self, other):
		if isinstance(other, Number):
			return Number(int(self.value <= other.value)).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def get_comparison_gte(self, other):
		if isinstance(other, Number):
			return Number(int(self.value >= other.value)).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def anded_by(self, other):
		if isinstance(other, Number):
			return Number(int(self.value and other.value)).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def ored_by(self, other):
		if isinstance(other, Number):
			return Number(int(self.value or other.value)).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def notted(self, other=None):
		return Number(1 if self.value == 0 else 0).set_context(self.context), None

	def copy(self):
		copy = Number(self.value)
		copy.set_pos(self.pos_start, self.pos_end)
		copy.set_context(self.context)
		return copy

	def is_true(self):
		return self.value != 0

	def __str__(self):
		return str(self.value)

	def __repr__(self):
		return str(self.value)

Number.null = Number(0)
Number.false = Number(0)
Number.true = Number(1)
Number.math_PI = Number(math.pi)

class String(Value):
	def __init__(self, value):
		super().__init__()
		self.value = value

	def added_to(self, other):
		if isinstance(other, String):
			return String(self.value + other.value).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def multed_by(self, other):
		if isinstance(other, Number):
			return String(self.value * other.value).set_context(self.context), None
		else:
			return None, Value.illegal_operation(self, other)

	def is_true(self):
		return len(self.value) > 0

	def copy(self):
		copy = String(self.value)
		copy.set_pos(self.pos_start, self.pos_end)
		copy.set_context(self.context)
		return copy

	def __str__(self):
		return self.value

	def __repr__(self):
		return f'"{self.value}"'

class List(Value):
	def __init__(self, elements):
		super().__init__()
		self.elements = elements

	def added_to(self, other):
		new_list = self.copy()
		new_list.elements.append(other)
		return new_list, None

	def subbed_by(self, other):
		if not isinstance(other, Number):
			return None, Value.illegal_operation(self, other)
		new_list = self.copy()
		try:
			new_list.elements.pop(other.value)
			return new_list, None
		except Exception:
			return None, RTError(
				other.pos_start, other.pos_end,
				'Element at this index could not be removed from list because index is out of bounds.',
				self.context
			)

	def multed_by(self, other):
		if not isinstance(other, List):
			return None, Value.illegal_operation(self, other)
		new_list = self.copy()
		new_list.elements.extend(other.elements)
		return new_list, None

	def dived_by(self, other):
		if not isinstance(other, Number):
			return None, Value.illegal_operation(self, other)
		try:
			return self.elements[other.value], None
		except Exception:
			return None, RTError(
				other.pos_start, other.pos_end,
				'Element at this index could not be retrieved from list because index is out of bounds.',
				self.context
			)

	def copy(self):
		copy = List(self.elements)
		copy.set_pos(self.pos_start, self.pos_end)
		copy.set_context(self.context)
		return copy

	def __str__(self):
		return ", ".join([str(x) for x in self.elements])

	def __repr__(self):
		return f'[{", ".join([repr(x) for x in self.elements])}]'

class BaseFunction(Value):
	def __init__(self, name):
		super().__init__()
		self.name = name or "<Unidentified>"

	def generate_new_context(self):
		new_context = Context(self.name, self.context, self.pos_start)
		new_context.symbol_table = SymbolTable(new_context.parent.symbol_table)
		return new_context

	def check_args(self, arg_names, args):
		res = RTResult()

		if len(args) > len(arg_names):
			return res.failure(RTError(
				self.pos_start, self.pos_end,
				f"{len(args) - len(arg_names)} too many arguments passed into {self}",
				self.context
			))
		
		if len(args) < len(arg_names):
			return res.failure(RTError(
				self.pos_start, self.pos_end,
				f"{len(arg_names) - len(args)} too few arguments passed into {self}",
				self.context
			))

		return res.success(None)

	def populate_args(self, arg_names, args, exec_ctx):
		for i in range(len(args)):
			arg_name = arg_names[i]
			arg_value = args[i]
			arg_value.set_context(exec_ctx)
			exec_ctx.symbol_table.set(arg_name, arg_value)

	def check_and_populate_args(self, arg_names, args, exec_ctx):
		res = RTResult()
		res.register(self.check_args(arg_names, args))
		if res.should_return(): return res
		self.populate_args(arg_names, args, exec_ctx)
		return res.success(None)

class Function(BaseFunction):
	def __init__(self, name, body_node, arg_names, should_auto_return):
		super().__init__(name)
		self.body_node = body_node
		self.arg_names = arg_names
		self.should_auto_return = should_auto_return

	def execute(self, args=None):
		res = RTResult()
		interpreter = Interpreter()
		exec_ctx = self.generate_new_context()

		res.register(self.check_and_populate_args(self.arg_names, args, exec_ctx))
		if res.should_return(): return res

		value = res.register(interpreter.visit(self.body_node, exec_ctx))
		if res.should_return() and res.func_return_value is None: return res

		ret_value = (value if self.should_auto_return else None) or res.func_return_value or Number.null
		return res.success(ret_value)

	def copy(self):
		copy = Function(self.name, self.body_node, self.arg_names, self.should_auto_return)
		copy.set_context(self.context)
		copy.set_pos(self.pos_start, self.pos_end)
		return copy

	def __repr__(self):
		return f"<function {self.name}>"

class BuiltInFunction(BaseFunction):
	def __init__(self, name):
		super().__init__(name)

	def execute(self, args=None):
		res = RTResult()
		exec_ctx = self.generate_new_context()

		method_name = f'execute_{self.name}'
		method = getattr(self, method_name, self.no_visit_method)

		res.register(self.check_and_populate_args(method.arg_names, args, exec_ctx))
		if res.should_return(): return res

		return_value = res.register(method(exec_ctx))
		return res if res.should_return() else res.success(return_value)

	def no_visit_method(self, node, context):
		raise AetherScriptError.call(f'No execute_{self.name} method defined')

	def copy(self):
		copy = BuiltInFunction(self.name)
		copy.set_context(self.context)
		copy.set_pos(self.pos_start, self.pos_end)
		return copy

	def __repr__(self):
		return f"<built-in function {self.name}>"

	def execute_print(self, exec_ctx):
		print(exec_ctx.symbol_table.get('value'))
		return RTResult().success(Number.null)
	execute_print.arg_names = ['value']

	def execute_print_ret(self, exec_ctx):
		return RTResult().success(String(str(exec_ctx.symbol_table.get('value'))))
	execute_print_ret.arg_names = ['value']

	def execute_input(self, exec_ctx):
		text = input()
		return RTResult().success(String(text))
	execute_input.arg_names = []

	def execute_input_int(self, exec_ctx):
		while True:
			text = input()
			try:
				number = int(text)
				break
			except ValueError:
				print(f"'{text}' must be an Integer. Try again!")
		return RTResult().success(Number(number))
	execute_input_int.arg_names = []

	def execute_clear(self, exec_ctx):
		os.system('cls')
		return RTResult().success(Number.null)
	execute_clear.arg_names = []

	def execute_is_number(self, exec_ctx):
		is_number = isinstance(exec_ctx.symbol_table.get("value"), Number)
		return RTResult().success(Number.true if is_number else Number.false)
	execute_is_number.arg_names = ["value"]

	def execute_is_string(self, exec_ctx):
		is_number = isinstance(exec_ctx.symbol_table.get("value"), String)
		return RTResult().success(Number.true if is_number else Number.false)
	execute_is_string.arg_names = ["value"]

	def execute_is_list(self, exec_ctx):
		is_number = isinstance(exec_ctx.symbol_table.get("value"), List)
		return RTResult().success(Number.true if is_number else Number.false)
	execute_is_list.arg_names = ["value"]

	def execute_is_function(self, exec_ctx):
		is_number = isinstance(exec_ctx.symbol_table.get("value"), BaseFunction)
		return RTResult().success(Number.true if is_number else Number.false)
	execute_is_function.arg_names = ["value"]

	def execute_append(self, exec_ctx):
		list_ = exec_ctx.symbol_table.get("list")
		value = exec_ctx.symbol_table.get("value")

		if not isinstance(list_, List):
			return RTResult().failure(RTError(
				self.pos_start, self.pos_end,
				"First argument must be list",
				exec_ctx
			))

		list_.elements.append(value)
		return RTResult().success(Number.null)
	execute_append.arg_names = ["list", "value"]

	def execute_pop(self, exec_ctx):
		list_ = exec_ctx.symbol_table.get("list")
		index = exec_ctx.symbol_table.get("index")

		if not isinstance(list_, List):
			return RTResult().failure(RTError(
				self.pos_start, self.pos_end,
				"First argument must be list.",
				exec_ctx
			))

		if not isinstance(index, Number):
			return RTResult().failure(RTError(
				self.pos_start, self.pos_end,
				"Second argument must be number.",
				exec_ctx
			))

		try:
			element = list_.elements.pop(index.value)
		except Exception:
			return RTResult().failure(RTError(
				self.pos_start, self.pos_end,
				'Element at this index could not be removed from list because index is out of bounds.',
				exec_ctx
			))
		return RTResult().success(element)
	execute_pop.arg_names = ["list", "index"]

	def execute_extend(self, exec_ctx):
		list_a = exec_ctx.symbol_table.get("listA")
		list_b = exec_ctx.symbol_table.get("listB")

		if not isinstance(list_a, List):
			return RTResult().failure(RTError(
				self.pos_start, self.pos_end,
				"First argument must be list",
				exec_ctx
			))

		if not isinstance(list_b, List):
			return RTResult().failure(RTError(
				self.pos_start, self.pos_end,
				"Second argument must be list",
				exec_ctx
			))

		list_a.elements.extend(list_b.elements)
		return RTResult().success(Number.null)
	execute_extend.arg_names = ["listA", "listB"]

	def execute_len(self, exec_ctx):
		list_ = exec_ctx.symbol_table.get("list")

		if not isinstance(list_, List):
			return RTResult().failure(RTError(
				self.pos_start, self.pos_end,
				"Argument must be list",
				exec_ctx
			))

		return RTResult().success(Number(len(list_.elements)))
	execute_len.arg_names = ["list"]

	def execute_run(self, exec_ctx):
		fn = exec_ctx.symbol_table.get("fn")

		if not isinstance(fn, String):
			return RTResult().failure(RTError(
				self.pos_start, self.pos_end,
				"Second argument must be string",
				exec_ctx
			))

		fn = fn.value

		try:
			with open(fn, "r") as f:
				script = f.read()
		except Exception as e:
			return RTResult().failure(
				RTError(
					self.pos_start,
					self.pos_end,
					f'Failed to load script \"{fn}\"\n{str(e)}',
					exec_ctx,
				)
			)

		_, error = run(fn, script)

		return (
			RTResult().failure(
				RTError(
					self.pos_start,
					self.pos_end,
					f'Failed to finish executing script \"{fn}\"\n{error.as_string()}',
					exec_ctx,
				)
			)
			if error
			else RTResult().success(Number.null)
		)
	execute_run.arg_names = ["fn"]

BuiltInFunction.print       = BuiltInFunction("print")
BuiltInFunction.print_ret   = BuiltInFunction("print_ret")
BuiltInFunction.input       = BuiltInFunction("input")
BuiltInFunction.input_int   = BuiltInFunction("input_int")
BuiltInFunction.clear       = BuiltInFunction("clear")
BuiltInFunction.is_number   = BuiltInFunction("is_number")
BuiltInFunction.is_string   = BuiltInFunction("is_string")
BuiltInFunction.is_list     = BuiltInFunction("is_list")
BuiltInFunction.is_function = BuiltInFunction("is_function")
BuiltInFunction.append      = BuiltInFunction("append")
BuiltInFunction.pop         = BuiltInFunction("pop")
BuiltInFunction.extend      = BuiltInFunction("extend")
BuiltInFunction.len					= BuiltInFunction("len")
BuiltInFunction.run					= BuiltInFunction("run")

class Context:
	def __init__(self, display_name, parent=None, parent_entry_pos=None):
		self.display_name = display_name
		self.parent = parent
		self.parent_entry_pos = parent_entry_pos
		self.symbol_table = None

class SymbolTable:
	def __init__(self, parent=None):
		self.symbols = {}
		self.parent = parent

	def get(self, name):
		value = self.symbols.get(name, None)
		return self.parent.get(name) if value is None and self.parent else value

	def set(self, name, value):
		self.symbols[name] = value

	def remove(self, name):
		del self.symbols[name]

class Interpreter:
	def visit(self, node, context):
		method_name = f'visit_{type(node).__name__}'
		method = getattr(self, method_name, self.no_visit_method)
		return method(node, context)

	def no_visit_method(self, node, context):
		raise AetherScriptError.call(f'No visit_{type(node).__name__} method defined')

	def visit_number_node(self, node, context):
		return RTResult().success(
			Number(node.tok.value).set_context(context).set_pos(node.pos_start, node.pos_end)
		)

	def visit_string_node(self, node, context):
		return RTResult().success(
			String(node.tok.value).set_context(context).set_pos(node.pos_start, node.pos_end)
		)

	def visit_list_node(self, node, context):
		res = RTResult()
		elements = []

		for element_node in node.element_nodes:
			elements.append(res.register(self.visit(element_node, context)))
			if res.should_return(): return res

		return res.success(
			List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
		)

	def visit_var_access_node(self, node, context):
		res = RTResult()
		var_name = node.var_name_tok.value
		value = context.symbol_table.get(var_name)

		if not value:
			return res.failure(RTError(
				node.pos_start, node.pos_end,
				f"'{var_name}' is not defined",
				context
			))

		value = value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
		return res.success(value)

	def visit_var_assign_node(self, node, context):
		res = RTResult()
		var_name = node.var_name_tok.value
		value = res.register(self.visit(node.value_node, context))
		if res.should_return(): return res

		context.symbol_table.set(var_name, value)
		return res.success(value)

	def visit_bin_op_node(self, node, context):
		res = RTResult()
		left = res.register(self.visit(node.left_node, context))
		if res.should_return(): return res
		right = res.register(self.visit(node.right_node, context))
		if res.should_return(): return res

		if node.op_tok.type == ttaddition:
			result, error = left.added_to(right)
		elif node.op_tok.type == ttsubstraction:
			result, error = left.subbed_by(right)
		elif node.op_tok.type == ttmultiplication:
			result, error = left.multed_by(right)
		elif node.op_tok.type == ttdivision:
			result, error = left.dived_by(right)
		elif node.op_tok.type == ttpower:
			result, error = left.powed_by(right)
		elif node.op_tok.type == ttee:
			result, error = left.get_comparison_eq(right)
		elif node.op_tok.type == ttne:
			result, error = left.get_comparison_ne(right)
		elif node.op_tok.type == ttlt:
			result, error = left.get_comparison_lt(right)
		elif node.op_tok.type == ttgt:
			result, error = left.get_comparison_gt(right)
		elif node.op_tok.type == ttlte:
			result, error = left.get_comparison_lte(right)
		elif node.op_tok.type == ttgte:
			result, error = left.get_comparison_gte(right)
		elif node.op_tok.matches(ttkeyword, 'And'):
			result, error = left.anded_by(right)
		elif node.op_tok.matches(ttkeyword, 'Or'):
			result, error = left.ored_by(right)

		if error:
			return res.failure(error)
		else:
			return res.success(result.set_pos(node.pos_start, node.pos_end))

	def visit_unary_op_node(self, node, context):
		res = RTResult()
		number = res.register(self.visit(node.node, context))
		if res.should_return(): return res

		error = None

		if node.op_tok.type == ttsubstraction:
			number, error = number.multed_by(Number(-1))
		elif node.op_tok.matches(ttkeyword, 'Not'):
			number, error = number.notted()

		if error:
			return res.failure(error)
		else:
			return res.success(number.set_pos(node.pos_start, node.pos_end))

	def visit_if_node(self, node, context):
		res = RTResult()

		for condition, expr, should_return_null in node.cases:
			condition_value = res.register(self.visit(condition, context))
			if res.should_return(): return res

			if condition_value.is_true():
				return self.return_expr_value(
					res, expr, context, should_return_null
				)
		if node.else_case:
			expr, should_return_null = node.else_case
			return self.return_expr_value(
				res, expr, context, should_return_null
			)
		return res.success(Number.null)

	def return_expr_value(self, res, expr, context, should_return_null):
		expr_value = res.register(self.visit(expr, context))
		if res.should_return(): return res
		return res.success(Number.null if should_return_null else expr_value)

	def visit_for_node(self, node, context):
		res = RTResult()
		elements = []

		start_value = res.register(self.visit(node.start_value_node, context))
		if res.should_return(): return res

		end_value = res.register(self.visit(node.end_value_node, context))
		if res.should_return(): return res

		if node.step_value_node:
			step_value = res.register(self.visit(node.step_value_node, context))
			if res.should_return(): return res
		else:
			step_value = Number(1)

		i = start_value.value

		if step_value.value >= 0:
			condition = lambda: i < end_value.value
		else:
			condition = lambda: i > end_value.value
		
		while condition():
			context.symbol_table.set(node.var_name_tok.value, Number(i))
			i += step_value.value

			value = res.register(self.visit(node.body_node, context))
			if res.should_return() and res.loop_should_continue == False and res.loop_should_break == False: return res
			
			if res.loop_should_continue:
				continue
			
			if res.loop_should_break:
				break

			elements.append(value)

		return res.success(
			Number.null if node.should_return_null else
			List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
		)

	def visit_while_node(self, node, context):
		res = RTResult()
		elements = []

		while True:
			condition = res.register(self.visit(node.condition_node, context))
			if res.should_return(): return res

			if not condition.is_true():
				break

			value = res.register(self.visit(node.body_node, context))
			if res.should_return() and res.loop_should_continue == False and res.loop_should_break == False: return res

			if res.loop_should_continue:
				continue
			
			if res.loop_should_break:
				break

			elements.append(value)

		return res.success(
			Number.null if node.should_return_null else
			List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
		)

	def visit_func_def_node(self, node, context):
		res = RTResult()

		func_name = node.var_name_tok.value if node.var_name_tok else None
		body_node = node.body_node
		arg_names = [arg_name.value for arg_name in node.arg_name_toks]
		func_value = Function(func_name, body_node, arg_names, node.should_auto_return).set_context(context).set_pos(node.pos_start, node.pos_end)
		
		if node.var_name_tok:
			context.symbol_table.set(func_name, func_value)

		return res.success(func_value)

	def visit_call_node(self, node, context):
		res = RTResult()
		args = []

		value_to_call = res.register(self.visit(node.node_to_call, context))
		if res.should_return(): return res
		value_to_call = value_to_call.copy().set_pos(node.pos_start, node.pos_end)

		for arg_node in node.arg_nodes:
			args.append(res.register(self.visit(arg_node, context)))
			if res.should_return(): return res

		return_value = res.register(value_to_call.execute(args))
		if res.should_return(): return res
		return_value = return_value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
		return res.success(return_value)

	def visit_return_node(self, node, context):
		res = RTResult()

		if node.node_to_return:
			value = res.register(self.visit(node.node_to_return, context))
			if res.should_return(): return res
		else:
			value = Number.null
		
		return res.success_return(value)

	def visit_continue_node(self):
		return RTResult().success_continue()

	def visit_break_node(self):
		return RTResult().success_break()

# set global symbols

global_symbol_table = SymbolTable()
global_symbol_table.set("Null", Number.null)
global_symbol_table.set("False", Number.false)
global_symbol_table.set("True", Number.true)
global_symbol_table.set("MathPi", Number.math_PI)
global_symbol_table.set("Write", BuiltInFunction.print)
global_symbol_table.set("Write_ret", BuiltInFunction.print_ret)
global_symbol_table.set("Input", BuiltInFunction.input)
global_symbol_table.set("Input_Int", BuiltInFunction.input_int)
global_symbol_table.set("Clear", BuiltInFunction.clear)
global_symbol_table.set("CLS", BuiltInFunction.clear)
global_symbol_table.set("IsNumber", BuiltInFunction.is_number)
global_symbol_table.set("IsString", BuiltInFunction.is_string)
global_symbol_table.set("IsList", BuiltInFunction.is_list)
global_symbol_table.set("IsFunction", BuiltInFunction.is_function)
global_symbol_table.set("Append", BuiltInFunction.append)
global_symbol_table.set("POP", BuiltInFunction.pop)
global_symbol_table.set("Extend", BuiltInFunction.extend)
global_symbol_table.set("Len", BuiltInFunction.len)
global_symbol_table.set("Run", BuiltInFunction.run)

# run

def run(fn, text):

	lexer = Lexer(fn, text)
	tokens, error = lexer.make_tokens()
	if error: return None, error

	parser = Parser(tokens)
	ast = parser.parse()
	if ast.error: return None, ast.error

	interpreter = Interpreter()
	context = Context('<program>')
	context.symbol_table = global_symbol_table
	result = interpreter.visit(ast.node, context)

	return result.value, result.error
