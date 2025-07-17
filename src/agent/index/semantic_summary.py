# Semantic summary generation for C codebases

import os
import tree_sitter_c as tsc
import tree_sitter
import json, sys
from collections import deque
from tree_sitter import Language, Parser
from typing import List
from init import askLLM

C_LANGUAGE = Language(tsc.language())
parser = Parser(C_LANGUAGE)

def find_nodes_by_type(root_node: tree_sitter.Node, node_type: str) -> List[tree_sitter.Node]:
    nodes = []
    if root_node.type == node_type:
        nodes.append(root_node)
    for child_node in root_node.children:
        nodes.extend(find_nodes_by_type(child_node, node_type))
    return nodes

def find_first_node_by_type(root_node: tree_sitter.Node, node_type: str) -> tree_sitter.Node:
    queue = deque([root_node])
    while queue:
        current_node = queue.popleft()
        if current_node.type == node_type:
            return current_node
        for child_node in current_node.children:
            queue.append(child_node)
    return None

def generate_function_summary(code: str) -> dict:
    prompt = f"""Analyze this C function and return JSON:
{{"summary": "one sentence description", "input": "parameters", "output": "return type"}}

Function:
```c
{code}
```"""
    
    while True:
        try:
            result = json.loads(askLLM(prompt))
            if all(k in result for k in ("summary", "input", "output")):
                return result
        except:
            continue

def generate_file_summary(function_map: dict) -> str:
    fn_summaries = "\n".join(f"- {name}: {info['summary']}" for name, info in function_map.items())
    return askLLM(f"Write a paragraph summary of this file:\n{fn_summaries}").strip()

def get_function_summaries(source_code, tree: tree_sitter.Tree):
    function_map = {}
    
    def extract_text(node):
        return source_code[node.start_byte:node.end_byte].decode("utf8")
    
    # Process function definitions
    for func_node in find_nodes_by_type(tree.root_node, "function_definition"):
        dec_node = find_first_node_by_type(func_node, "function_declarator")
        if dec_node:
            for sub_node in dec_node.children:
                if sub_node.type == "identifier":
                    function_name = extract_text(sub_node)
                    summary = generate_function_summary(extract_text(func_node))
                    function_map[function_name] = {
                        "start_byte": func_node.start_byte,
                        "end_byte": func_node.end_byte,
                        **summary
                    }
    
    # Process macro functions
    for func_node in find_nodes_by_type(tree.root_node, "preproc_function_def"):
        for sub_node in func_node.children:
            if sub_node.type == "identifier":
                function_name = extract_text(sub_node)
                summary = generate_function_summary(extract_text(func_node))
                function_map[function_name] = {
                    "start_byte": func_node.start_byte,
                    "end_byte": func_node.end_byte,
                    **summary
                }
    
    return function_map

def summarize_directory(directory: str, module_name=None) -> dict:
    if module_name is None:
        module_name = os.path.basename(os.path.normpath(directory))

    folder_summary = {"summary": "", "files": {}}
    all_file_summaries = []

    for entry in sorted(os.listdir(directory)):
        full_path = os.path.join(directory, entry)

        if os.path.isdir(full_path) and not entry.startswith("."):
            sub_summary = summarize_directory(full_path, module_name)
            folder_summary["files"][entry] = sub_summary
            all_file_summaries.append(f"{entry}/: {sub_summary['summary']}")

        elif entry.endswith((".c", ".h")):
            with open(full_path, "rb") as f:
                content = f.read()
            tree = parser.parse(content)
            function_list = get_function_summaries(content, tree)
            file_summary = generate_file_summary(function_list)
            folder_summary["files"][entry] = {"summary": file_summary, "functions": function_list}
            all_file_summaries.append(f"{entry}: {file_summary}")

    # Generate folder summary
    summaries_text = "\n".join(f"- {s}" for s in all_file_summaries)
    folder_summary["summary"] = askLLM(f'Write 1-2 sentences about folder "{os.path.basename(directory)}":\n{summaries_text}').strip()

    return folder_summary

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python semantic_summary.py /path/to/repo/")
        exit(1)

    directory = sys.argv[1]
    results = summarize_directory(directory)

    with open("summary_ripng.json", "w") as out:
        json.dump(results, out, indent=2)
