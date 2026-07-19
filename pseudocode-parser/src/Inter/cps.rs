//! Minimal value/type model required by the root `ast.rs`/`parser.rs` files.

use crate::Parser::ast::Expr;

#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Integer(i64),
    Real(f64),
    String(String),
    Char(char),
    Boolean(bool),
    Identifier(String),
}

#[derive(Debug, Clone, PartialEq)]
pub enum Type {
    Integer,
    Real,
    String,
    Char,
    Boolean,
    Array(ArrayType),
}

#[derive(Debug, Clone, PartialEq)]
pub struct ArrayType {
    pub lower_bound: Box<Expr>,
    pub upper_bound: Box<Expr>,
    pub bounds_2d: Option<(Box<Expr>, Box<Expr>)>,
    pub base_type: Box<Type>,
}
