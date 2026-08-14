//! CLI wrapper: parse Cambridge pseudocode and emit AST JSON.
//!
//! Usage:
//!   pseudocode-parser --format json --source-file answer.txt
//!   pseudocode-parser --format json --source "OUTPUT 1"
//!   echo 'OUTPUT 1' | pseudocode-parser
//!
//! Exit codes: 0 = ran (parse success or failure is reported in JSON `ok`),
//! 2 = usage or I/O error.

#![allow(non_snake_case)]
#![allow(dead_code)]

use std::io::Read;
use std::process::ExitCode;

use pseudocode_parser::parse_to_json;

struct CliArgs {
    format: String,
    source_file: Option<String>,
    source: Option<String>,
}

fn parse_cli_args() -> Result<CliArgs, String> {
    let mut args = std::env::args().skip(1);
    let mut format = "json".to_string();
    let mut source_file: Option<String> = None;
    let mut source: Option<String> = None;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--format" => {
                format = args.next().ok_or("--format requires a value")?;
            }
            "--source-file" => {
                source_file = Some(args.next().ok_or("--source-file requires a path")?);
            }
            "--source" => {
                source = Some(args.next().ok_or("--source requires source text")?);
            }
            "--help" | "-h" => {
                return Err("usage".to_string());
            }
            other => {
                return Err(format!("Unknown argument: {}", other));
            }
        }
    }

    if format != "json" {
        return Err(format!("Unsupported format: {} (only json)", format));
    }
    Ok(CliArgs {
        format,
        source_file,
        source,
    })
}

fn read_source(args: &CliArgs) -> Result<String, String> {
    if let Some(text) = &args.source {
        return Ok(text.clone());
    }
    if let Some(path) = &args.source_file {
        return std::fs::read_to_string(path)
            .map_err(|error| format!("Cannot read {}: {}", path, error));
    }
    let mut buffer = String::new();
    std::io::stdin()
        .read_to_string(&mut buffer)
        .map_err(|error| format!("Cannot read stdin: {}", error))?;
    Ok(buffer)
}

fn main() -> ExitCode {
    let args = match parse_cli_args() {
        Ok(args) => args,
        Err(message) => {
            eprintln!(
                "pseudocode-parser --format json [--source-file <path> | --source <text>]"
            );
            if message != "usage" {
                eprintln!("error: {}", message);
                return ExitCode::from(2);
            }
            return ExitCode::SUCCESS;
        }
    };

    let source = match read_source(&args) {
        Ok(source) => source,
        Err(message) => {
            eprintln!("error: {}", message);
            return ExitCode::from(2);
        }
    };

    println!("{}", parse_to_json(&source));
    ExitCode::SUCCESS
}
