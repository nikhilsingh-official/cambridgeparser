//! Lexer for Cambridge International pseudocode (9608/9618 style).
//!
//! Produces the token stream expected by the root `parser.rs`. Keywords are
//! the uppercase forms used in the Cambridge specification. A few tokens are
//! normalized away for parse coverage of common student notation:
//! `DO` (older `WHILE ... DO`), and `BYREF`/`BYVAL` parameter modes, which the
//! grammar does not model.

use crate::errortype::{CPSError, ErrorType};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum TokenType {
    // literals and names
    Identifier,
    NumberLiteral,
    StringLiteral,
    CharLiteral,
    True,
    False,
    // operators and punctuation
    Plus,
    Minus,
    Asterisk,
    ForwardSlash,
    Caret,
    Ampersand,
    Equal,
    NotEqual,
    LessThan,
    LessEqual,
    GreaterThan,
    GreaterEqual,
    Arrow,
    LParen,
    RParen,
    LSquare,
    RSquare,
    Colon,
    Comma,
    // keywords
    And,
    Or,
    Not,
    Mod,
    Div,
    Declare,
    Constant,
    If,
    Then,
    Else,
    EndIf,
    Case,
    Of,
    Otherwise,
    EndCase,
    While,
    EndWhile,
    Repeat,
    Until,
    For,
    To,
    Next,
    Procedure,
    EndProcedure,
    Function,
    Returns,
    EndFunction,
    Return,
    Call,
    Input,
    Output,
    OpenFile,
    ReadFile,
    WriteFile,
    CloseFile,
    Read,
    Write,
    Append,
    Type,
    EndType,
    EndClass,
    Set,
    Array,
    Integer,
    Real,
    String,
    Char,
    Boolean,
    Eof,
}

#[derive(Debug, Clone)]
pub struct Token {
    pub lexeme: String,
    pub token_type: TokenType,
    pub line: u32,
    pub column: u32,
}

impl Token {
    pub fn new(lexeme: String, token_type: TokenType, line: u32, column: u32) -> Self {
        Token {
            lexeme,
            token_type,
            line,
            column,
        }
    }
}

fn keyword_token(word: &str) -> Option<TokenType> {
    let token = match word {
        "AND" => TokenType::And,
        "OR" => TokenType::Or,
        "NOT" => TokenType::Not,
        "MOD" => TokenType::Mod,
        "DIV" => TokenType::Div,
        "DECLARE" => TokenType::Declare,
        "CONSTANT" => TokenType::Constant,
        "IF" => TokenType::If,
        "THEN" => TokenType::Then,
        "ELSE" => TokenType::Else,
        "ENDIF" => TokenType::EndIf,
        "CASE" => TokenType::Case,
        "OF" => TokenType::Of,
        "OTHERWISE" => TokenType::Otherwise,
        "ENDCASE" => TokenType::EndCase,
        "WHILE" => TokenType::While,
        "ENDWHILE" => TokenType::EndWhile,
        "REPEAT" => TokenType::Repeat,
        "UNTIL" => TokenType::Until,
        "FOR" => TokenType::For,
        "TO" => TokenType::To,
        "NEXT" => TokenType::Next,
        "PROCEDURE" => TokenType::Procedure,
        "ENDPROCEDURE" => TokenType::EndProcedure,
        "FUNCTION" => TokenType::Function,
        "RETURNS" => TokenType::Returns,
        "ENDFUNCTION" => TokenType::EndFunction,
        "RETURN" => TokenType::Return,
        "CALL" => TokenType::Call,
        "INPUT" => TokenType::Input,
        "OUTPUT" => TokenType::Output,
        "OPENFILE" => TokenType::OpenFile,
        "READFILE" => TokenType::ReadFile,
        "WRITEFILE" => TokenType::WriteFile,
        "CLOSEFILE" => TokenType::CloseFile,
        "READ" => TokenType::Read,
        "WRITE" => TokenType::Write,
        "APPEND" => TokenType::Append,
        "TYPE" => TokenType::Type,
        "ENDTYPE" => TokenType::EndType,
        "ENDCLASS" => TokenType::EndClass,
        "SET" => TokenType::Set,
        "ARRAY" => TokenType::Array,
        "INTEGER" => TokenType::Integer,
        "REAL" => TokenType::Real,
        "STRING" => TokenType::String,
        "CHAR" => TokenType::Char,
        "BOOLEAN" => TokenType::Boolean,
        "TRUE" => TokenType::True,
        "FALSE" => TokenType::False,
        _ => return None,
    };
    Some(token)
}

/// Words normalized away entirely: the grammar does not model them, and
/// dropping them lets standard Cambridge answers parse.
fn is_skipped_word(word: &str) -> bool {
    matches!(word, "DO" | "BYREF" | "BYVAL")
}

pub struct Lexer<'a> {
    chars: Vec<char>,
    position: usize,
    line: u32,
    column: u32,
    source: &'a str,
}

impl<'a> Lexer<'a> {
    pub fn new(source: &'a str) -> Self {
        Lexer {
            chars: source.chars().collect(),
            position: 0,
            line: 1,
            column: 1,
            source,
        }
    }

    fn peek(&self, n: usize) -> Option<char> {
        self.chars.get(self.position + n).copied()
    }

    fn advance(&mut self) -> Option<char> {
        let ch = self.chars.get(self.position).copied();
        if let Some(c) = ch {
            self.position += 1;
            if c == '\n' {
                self.line += 1;
                self.column = 1;
            } else {
                self.column += 1;
            }
        }
        ch
    }

    fn error(&self, message: String, hint: Option<String>) -> CPSError {
        CPSError {
            error_type: ErrorType::Syntax,
            message,
            hint,
            line: self.line,
            column: self.column,
            source: Some(self.source.to_string()),
        }
    }

    pub fn tokenize(mut self) -> Result<Vec<Token>, CPSError> {
        let mut tokens: Vec<Token> = Vec::new();

        while let Some(ch) = self.peek(0) {
            let line = self.line;
            let column = self.column;

            if ch.is_whitespace() {
                self.advance();
                continue;
            }

            // line comments
            if ch == '/' && self.peek(1) == Some('/') {
                while let Some(c) = self.peek(0) {
                    if c == '\n' {
                        break;
                    }
                    self.advance();
                }
                continue;
            }

            if ch.is_ascii_digit() {
                let mut lexeme = String::new();
                while let Some(c) = self.peek(0) {
                    if c.is_ascii_digit() {
                        lexeme.push(c);
                        self.advance();
                    } else if c == '.'
                        && self.peek(1).map_or(false, |d| d.is_ascii_digit())
                        && !lexeme.contains('.')
                    {
                        lexeme.push(c);
                        self.advance();
                    } else {
                        break;
                    }
                }
                tokens.push(Token::new(lexeme, TokenType::NumberLiteral, line, column));
                continue;
            }

            if ch.is_alphabetic() || ch == '_' {
                let mut lexeme = String::new();
                while let Some(c) = self.peek(0) {
                    if c.is_alphanumeric() || c == '_' {
                        lexeme.push(c);
                        self.advance();
                    } else {
                        break;
                    }
                }
                if is_skipped_word(&lexeme) {
                    continue;
                }
                match keyword_token(&lexeme) {
                    Some(token_type) => tokens.push(Token::new(lexeme, token_type, line, column)),
                    None => tokens.push(Token::new(lexeme, TokenType::Identifier, line, column)),
                }
                continue;
            }

            if ch == '"' {
                self.advance(); // opening quote
                let mut lexeme = String::new();
                let mut closed = false;
                while let Some(c) = self.advance() {
                    if c == '"' {
                        closed = true;
                        break;
                    }
                    if c == '\n' {
                        break;
                    }
                    lexeme.push(c);
                }
                if !closed {
                    return Err(self.error(
                        "Unterminated string literal".to_string(),
                        Some("String literals must be closed with a double quote".to_string()),
                    ));
                }
                tokens.push(Token::new(lexeme, TokenType::StringLiteral, line, column));
                continue;
            }

            if ch == '\'' {
                self.advance(); // opening quote
                let value = match self.advance() {
                    Some(c) if c != '\'' => c,
                    _ => {
                        return Err(self.error(
                            "Empty character literal".to_string(),
                            Some("Character literals must contain exactly one character".to_string()),
                        ))
                    }
                };
                match self.advance() {
                    Some('\'') => {}
                    _ => {
                        return Err(self.error(
                            "Unterminated character literal".to_string(),
                            Some("Character literals must be closed with a single quote".to_string()),
                        ))
                    }
                }
                tokens.push(Token::new(
                    value.to_string(),
                    TokenType::CharLiteral,
                    line,
                    column,
                ));
                continue;
            }

            // multi-character operators
            if ch == '<' {
                if self.peek(1) == Some('-') {
                    self.advance();
                    self.advance();
                    // tolerate long ASCII arrows such as `<--`
                    while self.peek(0) == Some('-') {
                        self.advance();
                    }
                    tokens.push(Token::new("<-".to_string(), TokenType::Arrow, line, column));
                    continue;
                }
                if self.peek(1) == Some('>') {
                    self.advance();
                    self.advance();
                    tokens.push(Token::new("<>".to_string(), TokenType::NotEqual, line, column));
                    continue;
                }
                if self.peek(1) == Some('=') {
                    self.advance();
                    self.advance();
                    tokens.push(Token::new("<=".to_string(), TokenType::LessEqual, line, column));
                    continue;
                }
                self.advance();
                tokens.push(Token::new("<".to_string(), TokenType::LessThan, line, column));
                continue;
            }

            if ch == '>' {
                if self.peek(1) == Some('=') {
                    self.advance();
                    self.advance();
                    tokens.push(Token::new(
                        ">=".to_string(),
                        TokenType::GreaterEqual,
                        line,
                        column,
                    ));
                    continue;
                }
                self.advance();
                tokens.push(Token::new(">".to_string(), TokenType::GreaterThan, line, column));
                continue;
            }

            let simple = match ch {
                '\u{2190}' | '\u{27F5}' | '\u{F0AC}' => Some(TokenType::Arrow),
                '\u{2260}' => Some(TokenType::NotEqual),
                '\u{2264}' => Some(TokenType::LessEqual),
                '\u{2265}' => Some(TokenType::GreaterEqual),
                '+' => Some(TokenType::Plus),
                '-' => Some(TokenType::Minus),
                '*' => Some(TokenType::Asterisk),
                '/' => Some(TokenType::ForwardSlash),
                '^' => Some(TokenType::Caret),
                '&' => Some(TokenType::Ampersand),
                '=' => Some(TokenType::Equal),
                '(' => Some(TokenType::LParen),
                ')' => Some(TokenType::RParen),
                '[' => Some(TokenType::LSquare),
                ']' => Some(TokenType::RSquare),
                ':' => Some(TokenType::Colon),
                ',' => Some(TokenType::Comma),
                _ => None,
            };

            if let Some(token_type) = simple {
                self.advance();
                tokens.push(Token::new(ch.to_string(), token_type, line, column));
                continue;
            }

            return Err(self.error(
                format!("Unexpected character: '{}'", ch),
                Some("This character is not part of Cambridge pseudocode".to_string()),
            ));
        }

        tokens.push(Token::new(String::new(), TokenType::Eof, self.line, self.column));
        Ok(tokens)
    }
}

pub fn tokenize(source: &str) -> Result<Vec<Token>, CPSError> {
    Lexer::new(source).tokenize()
}
