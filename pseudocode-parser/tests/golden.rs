//! Golden tests: run the compiled CLI against representative Cambridge
//! pseudocode and check the JSON contract.

use std::process::{Command, Stdio};
use std::io::Write;

fn run_parser(source: &str) -> serde_free_json::Json {
    let binary = env!("CARGO_BIN_EXE_pseudocode-parser");
    let mut child = Command::new(binary)
        .arg("--format")
        .arg("json")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("failed to launch pseudocode-parser");
    child
        .stdin
        .as_mut()
        .expect("stdin")
        .write_all(source.as_bytes())
        .expect("write source");
    let output = child.wait_with_output().expect("wait for parser");
    assert!(output.status.success(), "parser exited nonzero");
    let text = String::from_utf8(output.stdout).expect("utf8 output");
    serde_free_json::parse(&text)
}

/// Tiny dependency-free JSON reader sufficient for these assertions.
mod serde_free_json {
    #[derive(Debug, Clone, PartialEq)]
    pub enum Json {
        Null,
        Bool(bool),
        Number(f64),
        String(String),
        Array(Vec<Json>),
        Object(Vec<(String, Json)>),
    }

    impl Json {
        pub fn get(&self, key: &str) -> Option<&Json> {
            match self {
                Json::Object(entries) => entries
                    .iter()
                    .find(|(name, _)| name == key)
                    .map(|(_, value)| value),
                _ => None,
            }
        }

        pub fn as_bool(&self) -> Option<bool> {
            match self {
                Json::Bool(value) => Some(*value),
                _ => None,
            }
        }

        pub fn as_str(&self) -> Option<&str> {
            match self {
                Json::String(value) => Some(value),
                _ => None,
            }
        }

        pub fn as_array(&self) -> Option<&Vec<Json>> {
            match self {
                Json::Array(values) => Some(values),
                _ => None,
            }
        }
    }

    pub fn parse(text: &str) -> Json {
        let chars: Vec<char> = text.chars().collect();
        let mut position = 0usize;
        let value = parse_value(&chars, &mut position);
        value
    }

    fn skip_ws(chars: &[char], position: &mut usize) {
        while *position < chars.len() && chars[*position].is_whitespace() {
            *position += 1;
        }
    }

    fn parse_value(chars: &[char], position: &mut usize) -> Json {
        skip_ws(chars, position);
        match chars[*position] {
            '{' => parse_object(chars, position),
            '[' => parse_array(chars, position),
            '"' => Json::String(parse_string(chars, position)),
            't' => {
                *position += 4;
                Json::Bool(true)
            }
            'f' => {
                *position += 5;
                Json::Bool(false)
            }
            'n' => {
                *position += 4;
                Json::Null
            }
            _ => parse_number(chars, position),
        }
    }

    fn parse_object(chars: &[char], position: &mut usize) -> Json {
        let mut entries = Vec::new();
        *position += 1; // {
        loop {
            skip_ws(chars, position);
            if chars[*position] == '}' {
                *position += 1;
                break;
            }
            let key = parse_string(chars, position);
            skip_ws(chars, position);
            assert_eq!(chars[*position], ':');
            *position += 1;
            let value = parse_value(chars, position);
            entries.push((key, value));
            skip_ws(chars, position);
            if chars[*position] == ',' {
                *position += 1;
            }
        }
        Json::Object(entries)
    }

    fn parse_array(chars: &[char], position: &mut usize) -> Json {
        let mut values = Vec::new();
        *position += 1; // [
        loop {
            skip_ws(chars, position);
            if chars[*position] == ']' {
                *position += 1;
                break;
            }
            values.push(parse_value(chars, position));
            skip_ws(chars, position);
            if chars[*position] == ',' {
                *position += 1;
            }
        }
        Json::Array(values)
    }

    fn parse_string(chars: &[char], position: &mut usize) -> String {
        assert_eq!(chars[*position], '"');
        *position += 1;
        let mut out = String::new();
        while chars[*position] != '"' {
            if chars[*position] == '\\' {
                *position += 1;
                match chars[*position] {
                    'n' => out.push('\n'),
                    't' => out.push('\t'),
                    'r' => out.push('\r'),
                    'u' => {
                        let code: String = chars[*position + 1..*position + 5].iter().collect();
                        let value = u32::from_str_radix(&code, 16).unwrap_or(0);
                        out.push(char::from_u32(value).unwrap_or('\u{fffd}'));
                        *position += 4;
                    }
                    other => out.push(other),
                }
            } else {
                out.push(chars[*position]);
            }
            *position += 1;
        }
        *position += 1; // closing quote
        out
    }

    fn parse_number(chars: &[char], position: &mut usize) -> Json {
        let start = *position;
        while *position < chars.len()
            && (chars[*position].is_ascii_digit()
                || chars[*position] == '-'
                || chars[*position] == '+'
                || chars[*position] == '.'
                || chars[*position] == 'e'
                || chars[*position] == 'E')
        {
            *position += 1;
        }
        let text: String = chars[start..*position].iter().collect();
        Json::Number(text.parse().unwrap_or(0.0))
    }
}

fn statement_kinds(result: &serde_free_json::Json) -> Vec<String> {
    result
        .get("statements")
        .and_then(|value| value.as_array())
        .map(|statements| {
            statements
                .iter()
                .filter_map(|statement| {
                    statement
                        .get("kind")
                        .and_then(|kind| kind.as_str())
                        .map(str::to_string)
                })
                .collect()
        })
        .unwrap_or_default()
}

#[test]
fn function_with_if_loop_and_concat_parses() {
    let source = r#"
FUNCTION MakeString(Count : INTEGER, AChar : CHAR) RETURNS STRING
   DECLARE MyString : STRING
   DECLARE Index : INTEGER
   IF Count < 1 THEN
      MyString <- "ERROR"
   ELSE
      MyString <- ""
      FOR Index <- 1 TO Count
         MyString <- MyString & AChar
      NEXT Index
   ENDIF
   RETURN MyString
ENDFUNCTION
"#;
    let result = run_parser(source);
    assert_eq!(result.get("ok").and_then(|v| v.as_bool()), Some(true));
    assert_eq!(
        result.get("ast_version").and_then(|v| v.as_str()),
        Some("cambridge-pseudocode-ast/v1")
    );
    assert_eq!(statement_kinds(&result), vec!["function"]);
}

#[test]
fn unicode_arrow_and_operators_parse() {
    let source = "DECLARE Total : INTEGER\nTotal \u{2190} 1 + 2 * 3\nOUTPUT Total";
    let result = run_parser(source);
    assert_eq!(result.get("ok").and_then(|v| v.as_bool()), Some(true));
    assert_eq!(statement_kinds(&result), vec!["declare", "assignment", "output"]);
}

#[test]
fn while_case_repeat_and_files_parse() {
    let source = r#"
DECLARE i : INTEGER
WHILE i <= 10
  i <- i + 1
ENDWHILE
REPEAT
  i <- i - 1
UNTIL i = 0
CASE OF i
  1 : OUTPUT "one"
  2 TO 5 : OUTPUT "few"
  OTHERWISE : OUTPUT "many"
ENDCASE
OPENFILE "data.txt" FOR READ
READFILE "data.txt", i
CLOSEFILE "data.txt"
"#;
    let result = run_parser(source);
    assert_eq!(result.get("ok").and_then(|v| v.as_bool()), Some(true));
    assert_eq!(
        statement_kinds(&result),
        vec![
            "declare",
            "while",
            "repeat",
            "case",
            "open_file",
            "read_file",
            "close_file"
        ]
    );
}

#[test]
fn missing_endif_reports_error_diagnostic() {
    let result = run_parser("IF x > 1 THEN\nOUTPUT x");
    assert_eq!(result.get("ok").and_then(|v| v.as_bool()), Some(false));
    let diagnostics = result
        .get("diagnostics")
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    assert_eq!(diagnostics.len(), 1);
    let message = diagnostics[0]
        .get("message")
        .and_then(|value| value.as_str())
        .unwrap_or("")
        .to_string();
    assert!(message.contains("ENDIF"), "unexpected message: {}", message);
    assert_eq!(
        diagnostics[0].get("severity").and_then(|v| v.as_str()),
        Some("error")
    );
}

#[test]
fn lexer_error_is_reported_as_diagnostic_not_crash() {
    let result = run_parser("OUTPUT \"unterminated");
    assert_eq!(result.get("ok").and_then(|v| v.as_bool()), Some(false));
    let diagnostics = result
        .get("diagnostics")
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    assert_eq!(diagnostics.len(), 1);
}

#[test]
fn byref_and_do_are_normalized_away() {
    let source = r#"
PROCEDURE Swap(BYREF X : INTEGER, BYREF Y : INTEGER)
  DECLARE Temp : INTEGER
  Temp <- X
  X <- Y
  Y <- Temp
ENDPROCEDURE
WHILE TRUE DO
  OUTPUT 1
ENDWHILE
"#;
    let result = run_parser(source);
    assert_eq!(result.get("ok").and_then(|v| v.as_bool()), Some(true));
    assert_eq!(statement_kinds(&result), vec!["procedure", "while"]);
}
