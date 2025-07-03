import json
import os

from llmtool.LLM_utils import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from ui.logger import *

from typing import List, Dict, Tuple, Set


class AssumptionIdentifier:
    def __init__(
        self,
        model_name: str,
        temperature: float,
        language: str,
        max_query_num: int,
        logger: Logger,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.language = language
        self.max_query_num = max_query_num
        self.llm_utils = LLM(model_name, logger, temperature)
        self.logger = logger
        # Print debug info
        self.logger.print_console(f"AssumptionIdentifier initialized with model: {model_name}")
        return

    def identify_assumptions(self, function: Function, function_code: str) -> List[Value]:
        """
        Identify assumptions made in the given function code
        """
        self.logger.print_console(f"[DEBUG] Starting assumption identification for {function.function_name}")
        self.logger.print_log(f"Identifying assumptions for {function.function_name}")
        
        # Create a prompt to identify assumptions in the function
        system_prompt = self.build_system_prompt()
        user_prompt = self.build_user_prompt(function, function_code)
        
        # Print debug info about the prompts
        self.logger.print_console(f"[DEBUG] System prompt length: {len(system_prompt)}")
        self.logger.print_console(f"[DEBUG] User prompt length: {len(user_prompt)}")
        
        # Run LLM inference
        try:
            self.logger.print_console(f"[DEBUG] Calling LLM inference for function: {function.function_name}")
            response = self.llm_utils.infer(system_prompt + "\n\n" + user_prompt)
            self.logger.print_console(f"[DEBUG] Received LLM response of length: {len(response) if response else 0}")
            
            assumptions = self.parse_response(response, function)
            if assumptions:
                self.logger.print_log(f"Found {len(assumptions)} assumptions in {function.function_name}")
                self.logger.print_console(f"[DEBUG] Found {len(assumptions)} assumptions")
            else:
                self.logger.print_console(f"[DEBUG] No assumptions found or response parsing failed")
            return assumptions
        except Exception as e:
            self.logger.print_console(f"[DEBUG] Error in LLM inference: {str(e)}")
            self.logger.print_log(f"Error identifying assumptions in {function.function_name}: {str(e)}")
            return []

    def build_system_prompt(self) -> str:
        return f"""You are an expert code analyzer focusing on identifying implicit and explicit assumptions in source code. 
Your task is to analyze {self.language} code and identify assumptions that could lead to inconsistency issues if violated.

Types of assumptions to look for:
1. Null/None checking assumptions (e.g., parameters expected to be non-null)
2. Range/bound assumptions (e.g., values expected to be within a certain range)
3. State validity assumptions (e.g., objects expected to be in a certain state)
4. Call ordering assumptions (e.g., method A must be called before method B)
5. Resource management assumptions (e.g., caller will close a returned resource)
6. Thread safety assumptions (e.g., method is not thread-safe)
7. Exception handling assumptions (e.g., exceptions thrown under certain conditions)

Your analysis should be thorough and precise, focusing on assumptions that could lead to bugs if violated.
"""

    def build_user_prompt(self, function: Function, function_code: str) -> str:
        return f"""
Analyze the following {self.language} function and identify all implicit and explicit assumptions made in the code:

Function: {function.function_name}
Source code:
```{self.language}
{function_code}
```

Please identify all assumptions in this code that could lead to inconsistency if violated. For each assumption:
1. Describe the assumption precisely
2. Identify the line number where this assumption is relevant
3. Explain why violating this assumption would lead to a bug
4. Rate the severity of violating this assumption (Low, Medium, High)

Format your response as a JSON array where each element is a JSON object with the following fields:
- "assumption": String describing the assumption
- "line_number": Integer line number within the function (starting from 1)
- "var_name": String with variable or entity name this assumption applies to
- "violation_impact": String explaining the impact of violating this assumption
- "severity": String with severity level (Low, Medium, High)

Only return the JSON array. Do not include any other text in your response.
"""

    def parse_response(self, response: str, function: Function) -> List[Value]:
        """
        Parse LLM response and convert to Value objects
        """
        try:
            # Clean the response to extract only the JSON part
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Parse the JSON
            assumptions_json = json.loads(response)
            
            # Convert each assumption to a Value object
            assumptions = []
            for i, assumption_data in enumerate(assumptions_json):
                # Create a Value object for the assumption
                assumption = Value(
                    function_id=function.function_id,
                    line_number=assumption_data.get("line_number", 1),
                    label=ValueLabel.OTHER,
                    var_name=assumption_data.get("var_name", f"assumption_{i}"),
                    index=i,
                    is_sink=False,
                    metadata={
                        "assumption": assumption_data.get("assumption", ""),
                        "violation_impact": assumption_data.get("violation_impact", ""),
                        "severity": assumption_data.get("severity", "Medium")
                    }
                )
                assumptions.append(assumption)
            
            return assumptions
        except Exception as e:
            self.logger.print_log(f"Error parsing assumption response: {str(e)}")
            self.logger.print_log(f"Raw response: {response}")
            return [] 