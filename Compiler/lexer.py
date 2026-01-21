import re
import sys

# -----------------------------------------------------------------------------
# 1. Token Definition
# -----------------------------------------------------------------------------
class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        # Format: Line No | Token Type | Token Value
        return f"Line {self.line:<3} | {self.type:<20} | {self.value}"

# -----------------------------------------------------------------------------
# 2. Lumina Lexer Class
# -----------------------------------------------------------------------------
class LuminaLexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.tokens = []
        self.errors = []
        self.line_number = 1
        
        # Keywords
        self.keywords = {
            'func', 'main', 'let', 'var', 'type', 'struct', 'void', 'requires', 
            'ensures', 'invariant', 'old', 'result', 'if', 'else', 'switch', 
            'case', 'default', 'break', 'while', 'do', 'for', 'display', 'read',
            'return'
        }
        
        # Reserved Words
        self.reserved_words = {'true', 'false', 'null'}
        
        # Noise Words
        self.noise_words = {'that', 'the', 'is'}

    def tokenize(self):
        self.tokens = []
        self.errors = []
        self.line_number = 1

        # Regex Rules (Order Matters: specific/longer patterns first!)
        rules = [
            # Comments
            ('COMMENT_MULTI', r'/\*[\s\S]*?\*/'),
            ('COMMENT_SINGLE', r'//.*'),
            
            # Data Types
            # Matches strings allowing escaped quotes like \"
            ('STRING',        r'"(\\.|[^"\\])*"'), 
            ('UNTERM_STRING', r'"[^"\n]*'), 
            ('FLOAT',         r'\d+\.\d+'),
            ('INTEGER',       r'\d+'),
            
            # Compound Operators (Maximal Munch)
            ('OP_ARROW',       r'->'),
            ('OP_GUILLEMET_L', r'<<'), # Also Left Shift
            ('OP_GUILLEMET_R', r'>>'), # Also Right Shift
            
            ('OP_EQ',          r'=='),
            ('OP_NEQ',         r'!='),
            ('OP_GE',          r'>='),
            ('OP_LE',          r'<='),
            ('OP_AND',         r'&&'),
            ('OP_OR',          r'\|\|'),
            ('OP_INC',         r'\+\+'),
            ('OP_DEC',         r'--'),
            
            ('OP_ADD_ASS',     r'\+='),
            ('OP_SUB_ASS',     r'-='),
            ('OP_MUL_ASS',     r'\*='),
            ('OP_DIV_ASS',     r'/='),
            ('OP_MOD_ASS',     r'%='), 
            
            # Bitwise Operators
            ('OP_BIT_AND',     r'&'),
            ('OP_BIT_OR',      r'\|'),
            ('OP_BIT_XOR',     r'\^'),
            ('OP_BIT_NOT',     r'~'),

            # Single Character Symbols
            ('SYMBOL',         r'[+\-*/%=!><(){}\[\],;:\.]'),
            
            # Identifiers (Words)
            ('WORD',           r'[a-zA-Z_][a-zA-Z0-9_]*'),
            
            # Whitespace
            ('NEWLINE',        r'\n'),
            ('SKIP',           r'[ \t]+'),
            
            # Error Catching
            ('MISMATCH',       r'.'), 
        ]

        # Compile the master regex
        master_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in rules)
        
        for match in re.finditer(master_regex, self.source_code):
            kind = match.lastgroup
            value = match.group()
            
            if kind == 'NEWLINE':
                self.line_number += 1
                continue
            elif kind == 'SKIP':
                continue
            elif kind == 'COMMENT_SINGLE':
                continue
            elif kind == 'COMMENT_MULTI':
                self.line_number += value.count('\n')
                continue
            
            # --- Error Handling ---
            elif kind == 'UNTERM_STRING':
                self.errors.append(f"Lexical Error: Unterminated string literal on line {self.line_number}")
                self.tokens.append(Token('INVALID', value, self.line_number))
                continue
            elif kind == 'MISMATCH':
                self.errors.append(f"Lexical Error: Unexpected character '{value}' on line {self.line_number}")
                self.tokens.append(Token('INVALID', value, self.line_number))
                continue
            
            # --- Identifier Classification ---
            if kind == 'WORD':
                if value in self.keywords:
                    kind = 'KEYWORD'
                elif value in self.reserved_words:
                    kind = 'RESERVED_WORD'
                elif value in self.noise_words:
                    kind = 'NOISE_WORD'
                # Check for Types (PascalCase) vs Variables (snake_case)
                # Note: We treat words starting with _ as variables.
                elif value[0].isupper():
                    kind = 'ID_TYPE'
                else:
                    # Starts with lowercase OR underscore
                    kind = 'ID_VAR_FUNC'
            
            self.tokens.append(Token(kind, value, self.line_number))
            
        return self.tokens