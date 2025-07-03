import json
import os

from llmtool.LLM_utils import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from ui.logger import *

from typing import List, Dict, Tuple, Set


class ViolationAnalyzer:
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
        return

    def identify_potential_violations(
        self, function: Function, function_code: str, assumptions: List[Value]
    ) -> List[Value]:
        """
        Identify potential violations within the same function
        """
        self.logger.print_log(f"Identifying potential violations in {function.function_name}")
        
        if not assumptions:
            return []
        
        # Create a prompt to identify potential violations
        system_prompt = self.build_violation_system_prompt()
        
        # Format assumptions for the prompt
        assumptions_formatted = []
        for i, assumption in enumerate(assumptions):
            metadata = assumption.metadata if hasattr(assumption, "metadata") else {}
            assumptions_formatted.append({
                "id": i,
                "description": metadata.get("assumption", f"Assumption at line {assumption.line_number}"),
                "line_number": assumption.line_number,
                "var_name": assumption.var_name
            })
            
        user_prompt = self.build_violation_user_prompt(function, function_code, assumptions_formatted)
        
        # Run LLM inference
        try:
            response = self.llm_utils.infer(system_prompt + "\n\n" + user_prompt)
            violations = self.parse_violation_response(response, function)
            if violations:
                self.logger.print_log(f"Found {len(violations)} potential violations in {function.function_name}")
            return violations
        except Exception as e:
            self.logger.print_log(f"Error identifying violations in {function.function_name}: {str(e)}")
            return []

    def check_assumption_violation(
        self, caller: Function, call_context: str, callee: Function, assumption: Value
    ) -> bool:
        """
        Check if a caller might violate an assumption in the callee
        """
        self.logger.print_log(f"Checking if {caller.function_name} violates assumption in {callee.function_name}")
        
        # Get assumption metadata
        metadata = assumption.metadata if hasattr(assumption, "metadata") else {}
        assumption_desc = metadata.get("assumption", f"Assumption at line {assumption.line_number}")
        
        # Create a prompt to check if the caller violates the assumption
        system_prompt = self.build_violation_check_system_prompt()
        user_prompt = self.build_violation_check_user_prompt(
            caller, call_context, callee, assumption_desc, assumption.line_number
        )
        
        # Run LLM inference
        try:
            response = self.llm_utils.infer(system_prompt + "\n\n" + user_prompt)
            result = self.parse_violation_check_response(response)
            if result:
                self.logger.print_log(f"Found violation in {caller.function_name} for assumption in {callee.function_name}")
            return result
        except Exception as e:
            self.logger.print_log(f"Error checking violation in {caller.function_name}: {str(e)}")
            return False
    
    def verify_violation(
        self,
        function_with_assumption: Function,
        assumption_code: str,
        assumption: Value,
        function_with_violation: Function,
        violation_code: str,
        violation: Value
    ) -> bool:
        """
        Verify if a potential violation is a real violation
        """
        self.logger.print_log(f"Verifying violation between {function_with_assumption.function_name} and {function_with_violation.function_name}")
        
        # Get assumption metadata
        metadata = assumption.metadata if hasattr(assumption, "metadata") else {}
        assumption_desc = metadata.get("assumption", f"Assumption at line {assumption.line_number}")
        
        # Create a prompt to verify the violation
        system_prompt = self.build_verification_system_prompt()
        user_prompt = self.build_verification_user_prompt(
            function_with_assumption, assumption_code, assumption_desc, assumption.line_number,
            function_with_violation, violation_code, violation.line_number
        )
        
        # Run LLM inference
        try:
            response = self.llm_utils.infer(system_prompt + "\n\n" + user_prompt)
            result = self.parse_verification_response(response)
            if result:
                self.logger.print_log(f"Verified violation between {function_with_assumption.function_name} and {function_with_violation.function_name}")
            return result
        except Exception as e:
            self.logger.print_log(f"Error verifying violation: {str(e)}")
            return False

    def build_violation_system_prompt(self) -> str:
        return f"""You are an expert code analyzer focusing on identifying potential violations of implicit and explicit assumptions in source code.
Your task is to analyze {self.language} code and identify where assumptions might be violated within the same function.

Focus on identifying potential violations including:
1. Null/None dereferences
2. Out-of-bounds accesses
3. Use of uninitialized values
4. Resource leaks
5. Thread safety issues
6. Exception handling problems
7. Invariant violations

Your analysis should be thorough and precise, focusing on actual possible violations.
"""

    def build_violation_user_prompt(
        self, function: Function, function_code: str, assumptions: List[Dict]
    ) -> str:
        assumptions_text = "\n".join([
            f"{a['id']+1}. {a['description']} (line {a['line_number']}, variable: {a['var_name']})"
            for a in assumptions
        ])
        
        return f"""
Analyze the following {self.language} function to identify where the listed assumptions might be violated within the same function:

Function: {function.function_name}
Source code:
```{self.language}
{function_code}
```

Assumptions:
{assumptions_text}

For each assumption, identify where it might be violated within this function. Look for code paths where the assumption doesn't hold.

Format your response as a JSON array where each element is a JSON object with the following fields:
- "assumption_id": Integer ID of the assumption being violated (from the list above)
- "line_number": Integer line number where the violation occurs
- "var_name": String with variable name relevant to the violation
- "description": String explaining how the assumption is violated
- "severity": String with severity level (Low, Medium, High)

Only return the JSON array. Do not include any other text in your response.
"""

    def build_violation_check_system_prompt(self) -> str:
        return f"""You are an expert code analyzer focusing on identifying violations of assumptions across function boundaries.
Your task is to analyze {self.language} code to determine if a caller function violates assumptions made in a callee function.

Focus on identifying cross-function violations including:
1. Passing null/None when non-null is expected
2. Passing out-of-range values
3. Calling a function in the wrong order or state
4. Failing to handle resources properly
5. Violating thread safety assumptions
6. Mishandling exceptions

Your analysis should be thorough and precise. Answer with a clear yes/no and explanation.
"""

    def build_violation_check_user_prompt(
        self, caller: Function, call_context: str, callee: Function, assumption_desc: str, assumption_line: int
    ) -> str:
        return f"""
Analyze whether the following caller function might violate an assumption in the callee function:

Caller function: {caller.function_name}
Call context:
```{self.language}
{call_context}
```

Callee function: {callee.function_name}
Assumption in callee: "{assumption_desc}" (at line {assumption_line})

Does the caller potentially violate this assumption? Consider:
1. Is the caller passing appropriate parameters that satisfy the callee's assumptions?
2. Is the caller using the callee in the expected way (correct ordering, state, etc.)?
3. Is the caller handling resources returned by the callee appropriately?

Format your response as a JSON object with the following fields:
- "is_violated": Boolean (true if the assumption is potentially violated, false otherwise)
- "explanation": String explaining your reasoning
- "confidence": String with confidence level (Low, Medium, High)

Only return the JSON object. Do not include any other text in your response.
"""

    def build_verification_system_prompt(self) -> str:
        return f"""You are an expert code analyzer focusing on verifying potential inconsistency bugs across function boundaries.
Your task is to analyze {self.language} code to determine if a potential violation is a real violation.

For verification, you need to:
1. Trace the execution paths between the assumption and potential violation
2. Determine if there are actual code paths where the assumption does not hold
3. Check if there are guards or protections that prevent the violation
4. Assess the probability of the violation occurring in practice

Your analysis should be extremely thorough and precise. Provide a definitive answer with detailed reasoning.
"""

    def build_verification_user_prompt(
        self,
        function_with_assumption: Function,
        assumption_code: str,
        assumption_desc: str,
        assumption_line: int,
        function_with_violation: Function,
        violation_code: str,
        violation_line: int
    ) -> str:
        return f"""
Verify if the following potential violation is a real inconsistency bug:

Function with assumption: {function_with_assumption.function_name}
```{self.language}
{assumption_code}
```
Assumption: "{assumption_desc}" (at line {assumption_line})

Function with potential violation: {function_with_violation.function_name}
```{self.language}
{violation_code}
```
Potential violation at line {violation_line}

Perform deep analysis to verify if this is a real bug:
1. Is there a concrete execution path where the assumption is violated?
2. Are there guards or checks that prevent the violation?
3. What is the probability of this violation occurring in practice?
4. How serious would the consequences be if it did occur?

Format your response as a JSON object with the following fields:
- "is_verified": Boolean (true if this is a real bug, false if it's a false positive)
- "explanation": String with detailed reasoning
- "execution_path": String describing a possible execution path for the bug (if applicable)
- "severity": String with severity level (Low, Medium, High)
- "confidence": String with confidence level (Low, Medium, High)

Only return the JSON object. Do not include any other text in your response.
"""

    def parse_violation_response(self, response: str, function: Function) -> List[Value]:
        """
        Parse LLM response about violations and convert to Value objects
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
            violations_json = json.loads(response)
            
            # Convert each violation to a Value object
            violations = []
            for i, violation_data in enumerate(violations_json):
                # Create a Value object for the violation
                violation = Value(
                    function_id=function.function_id,
                    line_number=violation_data.get("line_number", 1),
                    label=ValueLabel.OTHER,
                    var_name=violation_data.get("var_name", f"violation_{i}"),
                    index=i,
                    is_sink=False,
                    metadata={
                        "assumption_id": violation_data.get("assumption_id", 0),
                        "description": violation_data.get("description", ""),
                        "severity": violation_data.get("severity", "Medium")
                    }
                )
                violations.append(violation)
            
            return violations
        except Exception as e:
            self.logger.print_log(f"Error parsing violation response: {str(e)}")
            self.logger.print_log(f"Raw response: {response}")
            return []

    def parse_violation_check_response(self, response: str) -> bool:
        """
        Parse LLM response about violation check
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
            result_json = json.loads(response)
            
            # Extract the result
            return result_json.get("is_violated", False)
        except Exception as e:
            self.logger.print_log(f"Error parsing violation check response: {str(e)}")
            self.logger.print_log(f"Raw response: {response}")
            return False

    def parse_verification_response(self, response: str) -> bool:
        """
        Parse LLM response about verification
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
            result_json = json.loads(response)
            
            # Extract the result
            return result_json.get("is_verified", False)
        except Exception as e:
            self.logger.print_log(f"Error parsing verification response: {str(e)}")
            self.logger.print_log(f"Raw response: {response}")
            return False 