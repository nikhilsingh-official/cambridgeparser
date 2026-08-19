// `ast.rs` and `parser.rs` sit beside this module rather than being declared
// inline so the two large files stay individually addressable; the crate
// wrapper never forks their contents.
pub mod ast;
pub mod parser;
