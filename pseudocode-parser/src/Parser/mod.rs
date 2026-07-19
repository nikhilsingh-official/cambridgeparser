// The AST and parser implementations live at the repository root; reference
// them in place so the crate wrapper never forks their contents.
#[path = "../../../ast.rs"]
pub mod ast;

#[path = "../../../parser.rs"]
pub mod parser;
