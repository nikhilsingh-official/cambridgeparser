//! Manual JSON serialization for the AST and diagnostics.
//!
//! Kept dependency-free so the crate builds offline; the AST shape is the
//! stable contract consumed by the Python adapter and grading prompts.

use crate::errortype::CPSError;
use crate::Inter::cps::{ArrayType, Type, Value};
use crate::Lexer::lexer::TokenType;
use crate::Parser::ast::{
    Ast, BinaryExpr, BlockStmt, CaseCondition, Expr, FileMode, Stmt, TypeDefinition,
};

pub const AST_VERSION: &str = "cambridge-pseudocode-ast/v1";

pub fn escape(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

fn string(text: &str) -> String {
    format!("\"{}\"", escape(text))
}

fn operator_symbol(token_type: &TokenType) -> &'static str {
    match token_type {
        TokenType::Plus => "+",
        TokenType::Minus => "-",
        TokenType::Asterisk => "*",
        TokenType::ForwardSlash => "/",
        TokenType::Caret => "^",
        TokenType::Ampersand => "&",
        TokenType::Mod => "MOD",
        TokenType::Div => "DIV",
        TokenType::And => "AND",
        TokenType::Or => "OR",
        TokenType::Equal => "=",
        TokenType::NotEqual => "<>",
        TokenType::LessThan => "<",
        TokenType::LessEqual => "<=",
        TokenType::GreaterThan => ">",
        TokenType::GreaterEqual => ">=",
        _ => "?",
    }
}

pub fn value_json(value: &Value) -> String {
    match value {
        Value::Integer(v) => format!("{{\"kind\":\"integer\",\"value\":{}}}", v),
        Value::Real(v) => {
            if v.fract() == 0.0 && v.is_finite() && v.abs() < 1e15 {
                format!("{{\"kind\":\"number\",\"value\":{}}}", *v as i64)
            } else {
                format!("{{\"kind\":\"number\",\"value\":{}}}", v)
            }
        }
        Value::String(v) => format!("{{\"kind\":\"string\",\"value\":{}}}", string(v)),
        Value::Char(v) => format!("{{\"kind\":\"char\",\"value\":{}}}", string(&v.to_string())),
        Value::Boolean(v) => format!("{{\"kind\":\"boolean\",\"value\":{}}}", v),
        Value::Identifier(v) => format!("{{\"kind\":\"identifier\",\"name\":{}}}", string(v)),
    }
}

pub fn type_json(type_: &Type) -> String {
    match type_ {
        Type::Integer => "{\"name\":\"INTEGER\"}".to_string(),
        Type::Real => "{\"name\":\"REAL\"}".to_string(),
        Type::String => "{\"name\":\"STRING\"}".to_string(),
        Type::Char => "{\"name\":\"CHAR\"}".to_string(),
        Type::Boolean => "{\"name\":\"BOOLEAN\"}".to_string(),
        Type::Array(array) => array_type_json(array),
    }
}

fn array_type_json(array: &ArrayType) -> String {
    let bounds_2d = match &array.bounds_2d {
        Some((lower, upper)) => format!(
            "{{\"lower\":{},\"upper\":{}}}",
            expr_json(lower),
            expr_json(upper)
        ),
        None => "null".to_string(),
    };
    format!(
        "{{\"name\":\"ARRAY\",\"lower_bound\":{},\"upper_bound\":{},\"bounds_2d\":{},\"base_type\":{}}}",
        expr_json(&array.lower_bound),
        expr_json(&array.upper_bound),
        bounds_2d,
        type_json(&array.base_type)
    )
}

pub fn ast_json(ast: &Ast) -> String {
    match ast {
        Ast::Identifier(name) => format!("{{\"kind\":\"identifier\",\"name\":{}}}", string(name)),
        Ast::Expression(expr) => expr_json(expr),
        Ast::Stmt(stmt) => stmt_json(stmt),
    }
}

pub fn expr_json(expr: &Expr) -> String {
    match expr {
        Expr::Binary(BinaryExpr {
            left,
            operator,
            right,
        }) => format!(
            "{{\"kind\":\"binary\",\"op\":{},\"left\":{},\"right\":{}}}",
            string(operator_symbol(operator)),
            ast_json(left),
            ast_json(right)
        ),
        Expr::Literal(value) => value_json(value),
        Expr::Call { name, arguments } => format!(
            "{{\"kind\":\"call\",\"name\":{},\"arguments\":[{}]}}",
            string(name),
            arguments
                .iter()
                .map(expr_json)
                .collect::<Vec<_>>()
                .join(",")
        ),
        Expr::ArrayAccess { name, index, col } => {
            let col_json = match col {
                Some(expr) => expr_json(expr),
                None => "null".to_string(),
            };
            format!(
                "{{\"kind\":\"array_access\",\"name\":{},\"index\":{},\"col\":{}}}",
                string(name),
                expr_json(index),
                col_json
            )
        }
        Expr::EOF { filename } => format!(
            "{{\"kind\":\"eof\",\"filename\":{}}}",
            string(filename)
        ),
    }
}

fn block_json(block: &BlockStmt) -> String {
    format!(
        "[{}]",
        block
            .statements
            .iter()
            .map(stmt_json)
            .collect::<Vec<_>>()
            .join(",")
    )
}

fn optional_block_json(block: &Option<BlockStmt>) -> String {
    match block {
        Some(inner) => block_json(inner),
        None => "null".to_string(),
    }
}

fn case_condition_json(condition: &CaseCondition) -> String {
    match condition {
        CaseCondition::Single(expr) => format!(
            "{{\"kind\":\"single\",\"value\":{}}}",
            expr_json(expr)
        ),
        CaseCondition::Range(from, to) => format!(
            "{{\"kind\":\"range\",\"from\":{},\"to\":{}}}",
            expr_json(from),
            expr_json(to)
        ),
    }
}

fn file_mode_json(mode: &FileMode) -> &'static str {
    match mode {
        FileMode::Read => "\"READ\"",
        FileMode::Write => "\"WRITE\"",
        FileMode::Append => "\"APPEND\"",
    }
}

fn parameters_json(parameters: &[(String, Type)]) -> String {
    format!(
        "[{}]",
        parameters
            .iter()
            .map(|(name, type_)| format!(
                "{{\"name\":{},\"type\":{}}}",
                string(name),
                type_json(type_)
            ))
            .collect::<Vec<_>>()
            .join(",")
    )
}

fn type_definition_json(definition: &TypeDefinition) -> String {
    match definition {
        TypeDefinition::Enumerated { name, values } => format!(
            "{{\"kind\":\"enumerated\",\"name\":{},\"values\":[{}]}}",
            string(name),
            values
                .iter()
                .map(|value| string(value))
                .collect::<Vec<_>>()
                .join(",")
        ),
        TypeDefinition::Pointer { name, points_to } => format!(
            "{{\"kind\":\"pointer\",\"name\":{},\"points_to\":{}}}",
            string(name),
            type_json(points_to)
        ),
        TypeDefinition::Record { name, fields } => format!(
            "{{\"kind\":\"record\",\"name\":{},\"fields\":[{}]}}",
            string(name),
            fields
                .iter()
                .map(|(field_name, field_type)| format!(
                    "{{\"name\":{},\"type\":{}}}",
                    string(field_name),
                    type_json(field_type)
                ))
                .collect::<Vec<_>>()
                .join(",")
        ),
        TypeDefinition::Set { name, base_type } => format!(
            "{{\"kind\":\"set\",\"name\":{},\"base_type\":{}}}",
            string(name),
            type_json(base_type)
        ),
    }
}

pub fn stmt_json(stmt: &Stmt) -> String {
    match stmt {
        Stmt::If {
            condition,
            then_branch,
            else_branch,
        } => format!(
            "{{\"kind\":\"if\",\"condition\":{},\"then\":{},\"else\":{}}}",
            expr_json(condition),
            block_json(then_branch),
            optional_block_json(else_branch)
        ),
        Stmt::Case {
            identifier,
            cases,
            otherwise,
        } => format!(
            "{{\"kind\":\"case\",\"subject\":{},\"cases\":[{}],\"otherwise\":{}}}",
            expr_json(identifier),
            cases
                .iter()
                .map(|(condition, block)| format!(
                    "{{\"condition\":{},\"statements\":{}}}",
                    case_condition_json(condition),
                    block_json(block)
                ))
                .collect::<Vec<_>>()
                .join(","),
            optional_block_json(otherwise)
        ),
        Stmt::While { condition, body } => format!(
            "{{\"kind\":\"while\",\"condition\":{},\"body\":{}}}",
            expr_json(condition),
            block_json(body)
        ),
        Stmt::Repeat { body, until } => format!(
            "{{\"kind\":\"repeat\",\"body\":{},\"until\":{}}}",
            block_json(body),
            expr_json(until)
        ),
        Stmt::For {
            identifier,
            start,
            end,
            body,
        } => format!(
            "{{\"kind\":\"for\",\"identifier\":{},\"start\":{},\"end\":{},\"body\":{}}}",
            string(identifier),
            expr_json(start),
            expr_json(end),
            block_json(body)
        ),
        Stmt::Assignment {
            identifier,
            array_index,
            value,
        } => {
            let index_json = match array_index {
                Some((row, col)) => {
                    let col_json = match col {
                        Some(expr) => expr_json(expr),
                        None => "null".to_string(),
                    };
                    format!(
                        "{{\"row\":{},\"col\":{}}}",
                        expr_json(row),
                        col_json
                    )
                }
                None => "null".to_string(),
            };
            format!(
                "{{\"kind\":\"assignment\",\"target\":{},\"array_index\":{},\"value\":{}}}",
                string(identifier),
                index_json,
                ast_json(value)
            )
        }
        Stmt::Constant { identifier, value } => format!(
            "{{\"kind\":\"constant\",\"name\":{},\"value\":{}}}",
            string(identifier),
            value_json(value)
        ),
        Stmt::Decleration { identifier, type_ } => format!(
            "{{\"kind\":\"declare\",\"name\":{},\"type\":{}}}",
            string(identifier),
            type_json(type_)
        ),
        Stmt::Input { identifier } => format!(
            "{{\"kind\":\"input\",\"target\":{}}}",
            expr_json(identifier)
        ),
        Stmt::Output { target } => format!(
            "{{\"kind\":\"output\",\"value\":{}}}",
            expr_json(target)
        ),
        Stmt::Block(block) => format!(
            "{{\"kind\":\"block\",\"statements\":{}}}",
            block_json(block)
        ),
        Stmt::Procedure {
            name,
            parameters,
            body,
        } => format!(
            "{{\"kind\":\"procedure\",\"name\":{},\"parameters\":{},\"body\":{}}}",
            string(name),
            parameters_json(parameters),
            block_json(body)
        ),
        Stmt::Function {
            name,
            parameters,
            return_type,
            body,
        } => format!(
            "{{\"kind\":\"function\",\"name\":{},\"parameters\":{},\"return_type\":{},\"body\":{}}}",
            string(name),
            parameters_json(parameters),
            type_json(return_type),
            block_json(body)
        ),
        Stmt::Return { value } => format!(
            "{{\"kind\":\"return\",\"value\":{}}}",
            expr_json(value)
        ),
        Stmt::Call { name, arguments } => format!(
            "{{\"kind\":\"call_statement\",\"name\":{},\"arguments\":[{}]}}",
            string(name),
            arguments
                .iter()
                .map(expr_json)
                .collect::<Vec<_>>()
                .join(",")
        ),
        Stmt::OpenFile { filename, mode } => format!(
            "{{\"kind\":\"open_file\",\"filename\":{},\"mode\":{}}}",
            expr_json(filename),
            file_mode_json(mode)
        ),
        Stmt::CloseFile { filename } => format!(
            "{{\"kind\":\"close_file\",\"filename\":{}}}",
            expr_json(filename)
        ),
        Stmt::ReadFile { filename, target } => format!(
            "{{\"kind\":\"read_file\",\"filename\":{},\"target\":{}}}",
            expr_json(filename),
            expr_json(target)
        ),
        Stmt::WriteFile { filename, value } => format!(
            "{{\"kind\":\"write_file\",\"filename\":{},\"value\":{}}}",
            expr_json(filename),
            expr_json(value)
        ),
        Stmt::TypeDef { type_definition } => format!(
            "{{\"kind\":\"type_definition\",\"definition\":{}}}",
            type_definition_json(type_definition)
        ),
    }
}

pub fn diagnostic_json(error: &CPSError) -> String {
    let hint = match &error.hint {
        Some(text) => string(text),
        None => "null".to_string(),
    };
    format!(
        "{{\"severity\":\"error\",\"message\":{},\"hint\":{},\"line\":{},\"column\":{}}}",
        string(&error.message),
        hint,
        error.line,
        error.column
    )
}

pub fn result_json(ok: bool, statements: &[Ast], diagnostics: &[CPSError]) -> String {
    format!(
        "{{\"ok\":{},\"ast_version\":{},\"statements\":[{}],\"diagnostics\":[{}],\"stdout\":\"\"}}",
        ok,
        string(AST_VERSION),
        statements
            .iter()
            .map(ast_json)
            .collect::<Vec<_>>()
            .join(","),
        diagnostics
            .iter()
            .map(diagnostic_json)
            .collect::<Vec<_>>()
            .join(",")
    )
}
