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
        return f"Line {self.line:<3} | {self.type:<20} | {self.value}"

# -----------------------------------------------------------------------------
# 2. Lumina Lexer Class
# -----------------------------------------------------------------------------
class LuminaLexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.tokens = []
        self.line_number = 1
        
        # Keywords
        self.keywords = {
            'func', 'main', 'let', 'var', 'type', 'struct', 'void', 'requires', 
            'ensures', 'invariant', 'old', 'result', 'if', 'else', 'switch', 
            'case', 'default', 'break', 'while', 'do', 'for', 'display', 'read'
        }
        
        # Reserved Words
        self.reserved_words = {'true', 'false', 'null'}
        
        # Noise Words
        self.noise_words = {'that', 'the', 'is'}

    def tokenize(self):
        rules = [
            ('COMMENT_MULTI', r'/\*[\s\S]*?\*/'),
            ('COMMENT_SINGLE', r'//.*'),
            ('STRING',        r'"[^"]*"'),
            ('FLOAT',         r'\d+\.\d+'),
            ('INTEGER',       r'\d+'),
            ('OP_ARROW',      r'->'),
            ('OP_GUILLEMET_L', r'<<'),
            ('OP_GUILLEMET_R', r'>>'),
            ('OP_EQ',         r'=='),
            ('OP_NEQ',        r'!='),
            ('OP_GE',         r'>='),
            ('OP_LE',         r'<='),
            ('OP_AND',        r'&&'),
            ('OP_OR',         r'\|\|'),
            ('OP_INC',        r'\+\+'),
            ('OP_DEC',        r'--'),
            ('OP_ADD_ASS',    r'\+='),
            ('OP_SUB_ASS',    r'-='),
            ('OP_MUL_ASS',    r'\*='),
            ('OP_DIV_ASS',    r'/='),
            ('SYMBOL',        r'[+\-*/%=!><(){}\[\],;:\.]'),
            ('WORD',          r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('NEWLINE',       r'\n'),
            ('SKIP',          r'[ \t]+'),
            ('MISMATCH',      r'.'),
        ]

        master_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in rules)
        
        for match in re.finditer(master_regex, self.source_code):
            kind = match.lastgroup
            value = match.group()
            
            if kind == 'NEWLINE':
                self.line_number += 1
                continue
            elif kind == 'SKIP':
                continue
            elif kind == 'COMMENT_SINGLE' or kind == 'COMMENT_MULTI':
                self.line_number += value.count('\n')
                continue
            elif kind == 'MISMATCH':
                # We can print errors, but for the GUI it's better to just skip or log
                print(f"Lexical Error: Unexpected character '{value}' on line {self.line_number}")
                continue
            
            if kind == 'WORD':
                if value in self.keywords:
                    kind = 'KEYWORD'
                elif value in self.reserved_words:
                    kind = 'RESERVED_WORD'
                elif value in self.noise_words:
                    kind = 'NOISE_WORD'
                elif value[0].isupper():
                    kind = 'ID_TYPE'
                elif value[0].islower():
                    kind = 'ID_VAR_FUNC'
            
            self.tokens.append(Token(kind, value, self.line_number))
            
        return self.tokens
