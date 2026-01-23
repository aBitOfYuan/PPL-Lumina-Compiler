import re
import difflib

# -----------------------------------------------------------------------------
# Token Definition
# -----------------------------------------------------------------------------
class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Line {self.line:<3} | {self.type:<20} | {self.value}"


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

        # Keywords
        self.keywords = {
            # Declarations & Structures
            'func', 'main', 'let', 'var', 'type', 'struct', 'void',
            
            # Primitive Types
            'int', 'char', 'bool', 'double', 'float', 'string',

            # Contracts & Verification
            'requires', 'ensures', 'invariant', 'old', 'result',
            
            # Control Flow
            'if', 'else', 'switch', 'case', 'default', 'break',
            'while', 'do', 'for', 'return',
            
            # I/O
            'display', 'read'
        }

        # Reserved literals
        self.reserved_words = {'null'} 

        # Noise words
        self.noise_words = {'that', 'the', 'is'}
        
        self.valid_noise_contexts = {
            'requires': 'that',
            'ensures':  'the',
            'type':     'is'
        }

        # Invalid keywords explicitly flagged
        self.invalid_keywords = {
            'function': "Invalid keyword. Use 'func'.",
            'elseif':   "Invalid keyword. Use 'else if'.",
            'print':    "Invalid keyword. Use 'display'."
        }
        
        self.primitive_types = {'int', 'char', 'bool', 'double', 'float', 'string'}

        # --- OPTIMIZATION: Combine all reserved words for typo checking ---
        # We create this list once here so we don't rebuild it for every token.
        self.all_vocab = list(self.keywords) + list(self.reserved_words) + ['true', 'false']

    # -----------------------------------------------------------------------------
    # Tokenization
    # -----------------------------------------------------------------------------
    def tokenize(self):
        self.tokens.clear()
        self.errors.clear()
        self.line_number = 1
        
        last_keyword = None 

        rules = [
            # --- 1. Comments ---
            ('COMMENT_MULTI',    r'/\*[\s\S]*?\*/'),
            ('COMMENT_SINGLE',   r'//.*'),
            ('ERR_UNTERM_CMT',   r'/\*[\s\S]*'),

            # --- 2. Invalid Literals & Identifiers ---
            ('ERR_FLOAT',        r'\d+\.\d+(\.\d+)+'),
            ('ERR_ID_DIGIT',     r'\d+[a-zA-Z_]+'),
            ('ERR_ID_HYPHEN',    r'[a-zA-Z_]\w*-\w+'), 

            # --- 3. Valid Literals ---
            ('CHAR_LITERAL',     r"'(\\.|[^'\\])'"),
            ('ERR_SINGLE_QUOTE', r"'[^']*'"), 
            ('STRING_LITERAL',   r'"(\\.|[^"\\])*"'),
            ('UNTERM_STRING',    r'"[^"\n]*'),
            ('FLOAT_LITERAL',    r'\d+\.\d+'),
            ('INTEGER_LITERAL',  r'\d+'),

            # --- 4. Invalid Operators ---
            ('ERR_OP_TRIPLE_EQ', r'==='),
            ('ERR_OP_REL_REV',   r'=<'),
            ('ERR_OP_DBL_NOT',   r'!!'),
            ('ERR_OP_DBL_DASH',  r'--(?=\d)'), 

            # --- 5. Valid Operators ---
            ('OP_ARROW',         r'->'),
            ('OP_EQ',            r'=='),
            ('OP_NEQ',           r'!='),
            ('OP_GE',            r'>='),
            ('OP_LE',            r'<='),
            ('OP_AND',           r'&&'),
            ('OP_OR',            r'\|\|'),
            ('OP_INC',           r'\+\+'),
            ('OP_DEC',           r'--'),
            ('OP_ADD_ASS',       r'\+='),
            ('OP_SUB_ASS',       r'-='),
            ('OP_MUL_ASS',       r'\*='),
            ('OP_DIV_ASS',       r'/='),
            ('OP_MOD_ASS',       r'%='),
            ('OP_SHL',           r'<<'),
            ('OP_SHR',           r'>>'),
            ('OP_BIT_AND',       r'&'),
            ('OP_BIT_OR',        r'\|'),
            ('OP_BIT_XOR',       r'\^'),
            ('OP_BIT_NOT',       r'~'),

            # --- 6. Symbols ---
            ('SYMBOL',           r'[+\-*/%=!><(){}\[\],;:\.\?]'),

            # --- 7. Illegal Characters ---
            ('ERR_ILLEGAL_CHAR', r'[@#]'),

            # --- 8. Identifiers / Keywords ---
            ('WORD',             r'[a-zA-Z_][a-zA-Z0-9_]*'),

            # --- 9. Whitespace ---
            ('NEWLINE',          r'\n'),
            ('SKIP',             r'[ \t]+'),

            # --- 10. Catch-all ---
            ('MISMATCH',         r'.'),
        ]

        master_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in rules)

        for match in re.finditer(master_regex, self.source_code):
            kind = match.lastgroup
            value = match.group()

            if kind == 'NEWLINE':
                self.line_number += 1
                continue
            if kind in {'SKIP', 'COMMENT_SINGLE'}:
                continue
            if kind == 'COMMENT_MULTI':
                self.line_number += value.count('\n')
                continue

            # --- Error Handling ---
            if kind == 'ERR_UNTERM_CMT':
                self._error("Unterminated multi-line comment")
                self.line_number += value.count('\n')
                self._add_token('INVALID', value)
                continue
            if kind == 'UNTERM_STRING':
                self._error("Unterminated string literal")
                self._add_token('INVALID', value)
                continue
            if kind == 'ERR_FLOAT':
                self._error(f"Invalid numeric literal '{value}'")
                self._add_token('INVALID', value)
                continue
            if kind == 'ERR_SINGLE_QUOTE':
                self._error(f"Invalid character literal '{value}'. Char literals must contain exactly one character.")
                self._add_token('INVALID', value)
                continue
            if kind == 'ERR_ID_DIGIT':
                self._error(f"Invalid identifier '{value}'. Cannot start with a digit.")
                self._add_token('INVALID', value)
                continue
            if kind == 'ERR_ID_HYPHEN':
                self._error(f"Invalid identifier '{value}'. Hyphens are not allowed.")
                self._add_token('INVALID', value)
                continue
            if kind == 'ERR_ILLEGAL_CHAR':
                self._error(f"Illegal character '{value}'.")
                self._add_token('INVALID', value)
                continue
            if kind.startswith('ERR_OP'):
                self._error(f"Invalid operator '{value}'.")
                self._add_token('INVALID', value)
                continue
            if kind == 'MISMATCH':
                self._error(f"Unexpected character '{value}'")
                self._add_token('INVALID', value)
                continue

            # --- Word Classification ---
            if kind == 'WORD':
                classification = self._classify_word(value, last_keyword)
                
                # Context-Sensitive Noise Word Check
                if classification == 'NOISE_WORD':
                    expected_noise = self.valid_noise_contexts.get(last_keyword)
                    if expected_noise != value:
                        self._error(f"Invalid noise word use. '{value}' is not valid after '{last_keyword}'.")
                        classification = 'INVALID'
                
                # Update Context
                if classification == 'KEYWORD':
                    last_keyword = value
                elif classification != 'NOISE_WORD':
                    last_keyword = None

                kind = classification
            else:
                last_keyword = None

            self._add_token(kind, value)

        self.tokens.append(Token('EOF', 'EOF', self.line_number))
        return self.tokens

    # -----------------------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------------------
    def _classify_word(self, value, last_keyword):
        # 1. Invalid Keywords (Explicitly forbidden map)
        if value in self.invalid_keywords:
            self._error(self.invalid_keywords[value])
            return 'INVALID'
        
        # 2. Boolean Literals
        if value in {'true', 'false'}:
            return 'BOOL_LITERAL'

        # 3. Valid Keywords (Exact Match)
        if value in self.keywords:
            # Context Check: Prevent using keywords as variable names
            strict_predecessors = {'func', 'struct', 'type'}.union(self.primitive_types)
            if last_keyword in strict_predecessors:
                # Exception 1: 'func main'
                if last_keyword == 'func' and value == 'main':
                    return 'KEYWORD'
                # Exception 2: Contracts after types
                if last_keyword in self.primitive_types and value in {'requires', 'ensures', 'invariant'}:
                    return 'KEYWORD'
                
                self._error(f"Invalid identifier '{value}'. Keywords cannot be used as names.")
                return 'INVALID'

            return 'KEYWORD'

        # 4. Reserved Literals
        if value in self.reserved_words:
            return 'RESERVED_WORD'

        # 5. Noise Words
        if value in self.noise_words:
            return 'NOISE_WORD'

        # ---------------------------------------------------------------------
        # STRICT SPELLING & TYPO ENFORCEMENT
        # ---------------------------------------------------------------------
        
        # Check A: Case Sensitivity (e.g., "While" instead of "while")
        if value.lower() in self.keywords:
             self._error(f"Keywords are case-sensitive. Did you mean '{value.lower()}'?")
             return 'INVALID'

        # Check B: Fuzzy Matching / Typo Detection
        # We perform this BEFORE classifying it as a variable.
        # If a word is 75% similar to a keyword, we assume it's a typo, not a variable.
        # We ignore very short words (len < 3) to avoid flagging 'x' or 'i' as typos of 'if'.
        if len(value) > 2:
            matches = difflib.get_close_matches(value, self.all_vocab, n=1, cutoff=0.75)
            if matches:
                suggestion = matches[0]
                self._error(f"Unknown identifier '{value}'. Did you mean keyword '{suggestion}'?")
                return 'INVALID'

        # ---------------------------------------------------------------------
        # CONTEXT ENFORCEMENT (Assign Specific ID Tokens)
        # ---------------------------------------------------------------------

        # If it passed the typo check, it is treated as an Identifier.

        # CASE 1: Function Identifier (after 'func')
        if last_keyword == 'func':
            if any(c.isupper() for c in value):
                self._error(f"Invalid function identifier '{value}'. Must be snake_case.")
                return 'INVALID'
            return 'ID_VAR_FUNC'

        # CASE 2: Type Identifier (after 'type' or 'struct')
        if last_keyword in {'type', 'struct'}:
            if not value[0].isupper():
                self._error(f"Invalid Type identifier '{value}'. Must start with Uppercase (PascalCase).")
                return 'INVALID'
            if '_' in value:
                self._error(f"Invalid Type identifier '{value}'. Cannot contain underscores.")
                return 'INVALID'
            return 'ID_VAR_TYPE'

        # CASE 3: Variable Identifier (after primitive types)
        if last_keyword in self.primitive_types:
            if value[0].isupper():
                self._error(f"Invalid variable identifier '{value}'. Variables must start with a lowercase letter.")
                return 'INVALID'
            if any(c.isupper() for c in value):
                self._error(f"Invalid variable identifier '{value}'. Must be snake_case (no uppercase).")
                return 'INVALID'
            return 'ID_VAR'

        # ---------------------------------------------------------------------
        # FALLBACK (General Usage)
        # ---------------------------------------------------------------------
        # If we see a standalone identifier, we enforce naming conventions.

        if value[0].isupper():
            if '_' in value:
                self._error(f"Invalid Type identifier '{value}'. Underscores allowed only in snake_case variables.")
                return 'INVALID'
            return 'ID_VAR_TYPE'
        
        return 'ID_VAR'

    def _add_token(self, kind, value):
        self.tokens.append(Token(kind, value, self.line_number))

    def _error(self, message):
        self.errors.append(f"Lexical Error (Line {self.line_number}): {message}")