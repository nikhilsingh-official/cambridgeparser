#[derive(Debug, Clone)]
pub enum ErrorType {
    Syntax,
}

#[derive(Debug, Clone)]
pub struct CPSError {
    pub error_type: ErrorType,
    pub message: String,
    pub hint: Option<String>,
    pub line: u32,
    pub column: u32,
    pub source: Option<String>,
}
