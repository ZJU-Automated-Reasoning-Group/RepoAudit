"""
Initialization utilities for LLM-based analysis tools.
"""

import os
from typing import Optional, Dict

from llmtool.LLM_utils import LLM
from ui.logger import Logger
from tstool.analyzer.TS_analyzer import TSAnalyzer
from tstool.analyzer.Python_TS_analyzer import Python_TSAnalyzer
from tstool.analyzer.Java_TS_analyzer import Java_TSAnalyzer
from tstool.analyzer.Cpp_TS_analyzer import Cpp_TSAnalyzer
from tstool.analyzer.Go_TS_analyzer import Go_TSAnalyzer


def create_ts_analyzer(code_in_files: Dict[str, str], language: str) -> TSAnalyzer:
    analyzers = {
        "python": Python_TSAnalyzer,
        "java": Java_TSAnalyzer,
        "cpp": Cpp_TSAnalyzer,
        "c++": Cpp_TSAnalyzer,
        "c": Cpp_TSAnalyzer,
        "go": Go_TSAnalyzer
    }
    
    analyzer_class = analyzers.get(language.lower())
    if not analyzer_class:
        raise ValueError(f"Unsupported language: {language}")
    
    lang_name = "Cpp" if language.lower() in ["cpp", "c++", "c"] else language.capitalize()
    return analyzer_class(code_in_files, lang_name)


def load_codebase(project_path: str, language: str) -> Dict[str, str]:
    extensions = {
        "python": [".py"],
        "java": [".java"],
        "cpp": [".cpp", ".cc", ".cxx", ".c", ".h", ".hpp"],
        "c": [".c", ".h"],
        "go": [".go"]
    }
    
    lang_extensions = extensions.get(language.lower(), [])
    if not lang_extensions:
        raise ValueError(f"Unsupported language: {language}")
    
    code_in_files = {}
    skip_dirs = {'.git', '__pycache__', 'node_modules', 'build', 'dist', 'target'}
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if any(file.endswith(ext) for ext in lang_extensions):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code_in_files[file_path] = f.read()
                except (UnicodeDecodeError, IOError) as e:
                    print(f"Warning: Could not read file {file_path}: {e}")
    
    return code_in_files


def create_logger(console: bool = True, log_file: Optional[str] = None) -> Logger:
    return Logger(console=console, log_file=log_file)


def create_llm_client(model_name: str = "gpt-4", temperature: float = 0.1, 
                     logger: Optional[Logger] = None) -> LLM:
    if logger is None:
        logger = create_logger()
    return LLM(model_name, logger, temperature)


def setup_analysis_environment(project_path: str, language: str, model_name: str = "gpt-4",
                              temperature: float = 0.1, logger: Optional[Logger] = None) -> tuple[TSAnalyzer, LLM, Logger]:
    if logger is None:
        logger = create_logger()
    
    code_in_files = load_codebase(project_path, language)
    ts_analyzer = create_ts_analyzer(code_in_files, language)
    llm_client = create_llm_client(model_name, temperature, logger)
    
    return ts_analyzer, llm_client, logger


def quick_llm_query(prompt: str, model_name: str = "gpt-4", temperature: float = 0.1,
                   logger: Optional[Logger] = None) -> str:
    llm_client = create_llm_client(model_name, temperature, logger)
    response, _, _ = llm_client.infer(prompt, is_measure_cost=False)
    return response


def askLLM(prompt: str, model_name: str = "gpt-4") -> str:
    """Backward compatibility function"""
    return quick_llm_query(prompt, model_name)
