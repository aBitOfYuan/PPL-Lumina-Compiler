import re

# -----------------------------------------------------------------------------
# Token Definition
# -----------------------------------------------------------------------------
class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Line {self.line:<3} | {self.type:<18} | {self.value}"


# -----------------------------------------------------------------------------
# Lumina Lexer
# -----------------------------------------------------------------------------
class LuminaLexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.tokens = []
        self.errors = []
        self.line_number = 1

        # ---------------- Language Sets ----------------

        # Keywords (control + data types)
        self.keywords = {
            # Control / structure
            'func', 'main', 'let', 'var', 'type', 'struct', 'void',
            'requires', 'ensures', 'invariant', 'old', 'result',
            'if', 'else', 'switch', 'case', 'default', 'break',
            'while', 'do', 'for', 'return', 'display', 'read',

            # Data types
            'int', 'char', 'bool', 'double', 'float', 'string'
        }

        # Reserved literals
        self.reserved_words = {'true', 'false', 'null'}

        # Noise words
        self.noise_words = {'that', 'the', 'is'}

        # Invalid keywords
        self.invalid_keywords = {'print'}

    # -----------------------------------------------------------------------------
    # Tokenization
    # -----------------------------------------------------------------------------
    def tokenize(self):
        self.tokens.clear()
        self.errors.clear()
        self.line_number = 1

        rules = [
            # Comments
            ('COMMENT_MULTI',   r'/\*[\s\S]*?\*/'),
            ('COMMENT_SINGLE',  r'//.*'),

            # Literals
            ('STRING',          r'"(\\.|[^"\\])*"'),
            ('UNTERM_STRING',   r'"[^"\n]*'),
            ('FLOAT',           r'\d+\.\d+'),
            ('INTEGER',         r'\d+'),

            # Operators (longest first)
            ('OP_ARROW',        r'->'),
            ('OP_EQ',           r'=='),
            ('OP_NEQ',          r'!='),
            ('OP_GE',           r'>='),
            ('OP_LE',           r'<='),
            ('OP_AND',          r'&&'),
            ('OP_OR',           r'\|\|'),
            ('OP_INC',          r'\+\+'),
            ('OP_DEC',          r'--'),
            ('OP_ADD_ASS',      r'\+='),
            ('OP_SUB_ASS',      r'-='),
            ('OP_MUL_ASS',      r'\*='),
            ('OP_DIV_ASS',      r'/='),
            ('OP_MOD_ASS',      r'%='),

            # Bitwise
            ('OP_SHL',          r'<<'),
            ('OP_SHR',          r'>>'),
            ('OP_BIT_AND',      r'&'),
            ('OP_BIT_OR',       r'\|'),
            ('OP_BIT_XOR',      r'\^'),
            ('OP_BIT_NOT',      r'~'),

            # Symbols
            ('SYMBOL',          r'[+\-*/%=!><(){}\[\],;:\.]'),

            # Identifiers / Keywords
            ('WORD',            r'[a-zA-Z_][a-zA-Z0-9_]*'),

            # Whitespace
            ('NEWLINE',         r'\n'),
            ('SKIP',            r'[ \t]+'),

            # Catch-all
            ('MISMATCH',        r'.'),
        ]

        master_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in rules)

        for match in re.finditer(master_regex, self.source_code):
            kind = match.lastgroup
            value = match.group()

            # --- Whitespace & Comments ---
            if kind == 'NEWLINE':
                self.line_number += 1
                continue

            if kind in {'SKIP', 'COMMENT_SINGLE'}:
                continue

            if kind == 'COMMENT_MULTI':
                self.line_number += value.count('\n')
                continue

            # --- Errors ---
            if kind == 'UNTERM_STRING':
                self._error("Unterminated string literal")
                self._add_token('INVALID', value)
                continue

            if kind == 'MISMATCH':
                self._error(f"Unexpected character '{value}'")
                self._add_token('INVALID', value)
                continue

            # --- Identifier Classification ---
            if kind == 'WORD':
                kind = self._classify_word(value)

            self._add_token(kind, value)

        # End of File
        self.tokens.append(Token('EOF', 'EOF', self.line_number))
        return self.tokens

    # -----------------------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------------------
    def _classify_word(self, value):
        if value in self.invalid_keywords:
            self._error(f"Invalid keyword '{value}'. Use 'display' instead.")
            return 'INVALID'

        if value in self.keywords:
            return 'KEYWORD'

        if value in self.reserved_words:
            return 'RESERVED_WORD'

        if value in self.noise_words:
            return 'NOISE_WORD'

        if value[0].isupper():
            return 'ID_TYPE'

        return 'IDENTIFIER'

    def _add_token(self, kind, value):
        self.tokens.append(Token(kind, value, self.line_number))

    def _error(self, message):
        self.errors.append(f"Lexical Error (Line {self.line_number}): {message}")
