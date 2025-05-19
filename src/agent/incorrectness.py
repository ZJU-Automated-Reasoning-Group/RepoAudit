import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
import time
import copy

from agent.agent import *

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from llmtool.LLM_utils import *
from llmtool.incorrectness.assumption_identifier import *
from llmtool.incorrectness.violation_analyzer import *

from memory.semantic.incorrectness_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from ui.logger import *

BASE_PATH = Path(__file__).resolve().parents[2]


class IncorrectnessAgent(Agent):
    def __init__(
        self,
        project_path,
        language,
        ts_analyzer,
        model_name,
        temperature,
        max_neural_workers=1,
        agent_id: int = 0,
    ) -> None:
        self.project_path = project_path
        self.project_name = project_path.split("/")[-1]
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.ts_analyzer = ts_analyzer

        self.model_name = model_name
        self.temperature = temperature
        self.max_neural_workers = max_neural_workers
        self.MAX_QUERY_NUM = 5

        self.lock = threading.Lock()

        with self.lock:
            self.log_dir_path = f"{BASE_PATH}/log/incorrectness/{self.model_name}/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}-{agent_id}"
            self.res_dir_path = f"{BASE_PATH}/result/incorrectness/{self.model_name}/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}-{agent_id}"
            if not os.path.exists(self.log_dir_path):
                os.makedirs(self.log_dir_path)
            self.logger = Logger(self.log_dir_path + "/" + "incorrectness.log")

            if not os.path.exists(self.res_dir_path):
                os.makedirs(self.res_dir_path)

        # LLM tools for incorrectness logic analysis
        self.assumption_identifier = AssumptionIdentifier(
            self.model_name,
            self.temperature,
            self.language,
            self.MAX_QUERY_NUM,
            self.logger,
        )
        self.violation_analyzer = ViolationAnalyzer(
            self.model_name,
            self.temperature,
            self.language,
            self.MAX_QUERY_NUM,
            self.logger,
        )

        # Initialize state with empty lists - to be populated during analysis
        self.state = IncorrectnessState([], [])
        return

    def identify_assumptions_and_assertions(self) -> None:
        """
        First phase: identify assumptions and assertions in the codebase
        """
        self.logger.print_log("Starting identification of assumptions and assertions")
        
        # Process functions in parallel
        with ThreadPoolExecutor(max_workers=self.max_neural_workers) as executor:
            futures = []
            for function_id, function in tqdm(self.ts_analyzer.function_env.items(), desc="Processing functions"):
                futures.append(executor.submit(self.__process_function, function))
            
            # Collect results
            for future in tqdm(as_completed(futures), total=len(futures), desc="Collecting results"):
                try:
                    future.result()
                except Exception as e:
                    self.logger.print_log(f"Error processing function: {str(e)}")
        
        # Save identified assumptions and assertions
        with open(f"{self.res_dir_path}/assumptions.json", "w") as f:
            json.dump({k: [v.__dict__ for v in vs] for k, vs in self.state.assumption_points.items()}, f, indent=2)
        
        self.logger.print_log("Completed identification of assumptions and assertions")
        return

    def __get_function_code(self, function: Function) -> str:
        """
        Helper method to extract function code since get_function_code_from_file() doesn't exist
        """
        try:
            file_path = function.file_path
            file_content = self.ts_analyzer.code_in_files[file_path]
            
            # Extract function content based on line numbers
            lines = file_content.split('\n')
            start_line = function.start_line_number - 1  # 0-indexed
            end_line = function.end_line_number - 1  # 0-indexed
            
            # Get relevant lines
            function_code = '\n'.join(lines[start_line:end_line+1])
            
            self.logger.print_console(f"[DEBUG] Extracted code for {function.function_name}: {len(function_code)} chars")
            return function_code
        except Exception as e:
            self.logger.print_console(f"[DEBUG] Error extracting function code: {str(e)}")
            return ""

    def __process_function(self, function: Function) -> None:
        """
        Process a single function to identify assumptions and assertions
        """
        try:
            # Extract function context using our helper method
            function_code = self.__get_function_code(function)
            if not function_code:
                self.logger.print_console(f"[DEBUG] No code found for function {function.function_name}")
                return
            
            self.logger.print_console(f"[DEBUG] Processing function {function.function_name} with {len(function_code)} characters")
            
            # Identify assumptions using LLM
            assumptions = self.assumption_identifier.identify_assumptions(function, function_code)
            if assumptions:
                for assumption in assumptions:
                    self.state.update_assumption_points(function.function_id, assumption)
            
            # Identify potential violations
            violations = self.violation_analyzer.identify_potential_violations(function, function_code, assumptions)
            if violations:
                for violation in violations:
                    # Add to the potential violations list
                    self.state.potential_violations.append(violation)
                    
                    # Create initial context
                    assumption_context = CallContext()
                    violation_context = CallContext()
                    
                    # Add to violation paths
                    for assumption in assumptions:
                        assumption_with_context = (assumption, assumption_context)
                        violation_with_context = (violation, violation_context)
                        self.state.update_violation_paths(
                            assumption_with_context, 
                            set([violation_with_context])
                        )
        except Exception as e:
            self.logger.print_console(f"[DEBUG] Error in process_function: {str(e)}")
            self.logger.print_log(f"Error processing function {function.function_name}: {str(e)}")
        return

    def analyze_cross_function_violations(self) -> None:
        """
        Second phase: analyze cross-function interactions for assumption violations
        """
        self.logger.print_log("Starting cross-function violation analysis")
        
        # Identify functions with assumptions
        functions_with_assumptions = set(self.state.assumption_points.keys())
        
        # For each function with assumptions, check functions that call it
        for function_id in functions_with_assumptions:
            function = self.ts_analyzer.function_env[function_id]
            caller_functions = self.ts_analyzer.get_all_caller_functions(function)
            
            # Check if callers respect the assumptions
            for caller in caller_functions:
                self.__analyze_caller_assumption_matching(function, caller)
        
        self.logger.print_log("Completed cross-function violation analysis")
        return

    def __get_code_around_call_site(self, function: Function, call_site) -> str:
        """
        Helper method to extract code around a call site
        """
        try:
            file_path = function.file_path
            file_content = self.ts_analyzer.code_in_files[file_path]
            
            # Find the line of the call site
            call_site_line = file_content[:call_site.start_byte].count('\n') + 1
            
            # Extract context (3 lines before and after)
            lines = file_content.split('\n')
            start_line = max(0, call_site_line - 4)  # 0-indexed, with 3 lines before
            end_line = min(len(lines) - 1, call_site_line + 2)  # 0-indexed, with 3 lines after
            
            call_context = '\n'.join(lines[start_line:end_line+1])
            self.logger.print_console(f"[DEBUG] Extracted call context: {len(call_context)} chars")
            return call_context
        except Exception as e:
            self.logger.print_console(f"[DEBUG] Error extracting call context: {str(e)}")
            return ""

    def __analyze_caller_assumption_matching(self, callee: Function, caller: Function) -> None:
        """
        Analyze if caller respects assumptions in callee
        """
        # Skip if no assumptions for callee
        if callee.function_id not in self.state.assumption_points:
            return
        
        # Get all assumptions for callee
        assumptions = self.state.assumption_points[callee.function_id]
        
        # Get caller code
        caller_code = self.__get_function_code(caller)
        if not caller_code:
            return
        
        # Get call sites from caller to callee
        call_sites = self.ts_analyzer.get_callsites_by_callee_name(caller, callee.function_name)
        
        for call_site in call_sites:
            # Extract call context
            call_context_code = self.__get_code_around_call_site(caller, call_site)
            
            # Check if any assumptions are violated at this call site
            for assumption in assumptions:
                is_violated = self.violation_analyzer.check_assumption_violation(
                    caller, call_context_code, callee, assumption
                )
                
                if is_violated:
                    # Create contexts
                    caller_context = CallContext()
                    callee_context = CallContext()
                    
                    # Create violation value
                    violation_value = Value(
                        function_id=caller.function_id,
                        line_number=self.__get_line_number_for_call_site(caller, call_site),
                        label=ValueLabel.OTHER,
                        var_name=f"violation_at_call_{callee.function_name}",
                        index=0,
                        is_sink=False
                    )
                    
                    # Update cross-function violations
                    self.state.update_cross_function_violations(
                        (assumption, callee_context),
                        set([(violation_value, caller_context)])
                    )
                    
                    # Create a bug report
                    self.__create_bug_report(assumption, violation_value, caller, callee)
        return

    def __get_line_number_for_call_site(self, function: Function, call_site) -> int:
        """
        Get the line number for a call site
        """
        file_content = self.ts_analyzer.code_in_files[function.file_path]
        line_number = file_content[:call_site.start_byte].count("\n") + 1
        return line_number

    def __create_bug_report(self, assumption: Value, violation: Value, caller: Function, callee: Function) -> None:
        """
        Create a bug report for a violation
        """
        # Get basic information
        function_with_assumption = self.ts_analyzer.function_env[assumption.function_id]
        function_with_violation = caller
        
        # Create a report
        bug_report = BugReport()
        bug_report.bug_type = "Incorrectness"
        bug_report.file_path = function_with_violation.file_path
        bug_report.function_name = function_with_violation.function_name
        bug_report.line_number = violation.line_number
        bug_report.description = f"Potential assumption violation at call to {callee.function_name}. " \
                                f"Assumption in {function_with_assumption.function_name} (line {assumption.line_number}) " \
                                f"may be violated by caller {function_with_violation.function_name}."
        
        # Add the bug report
        self.state.update_bug_report(bug_report)
        
        # Save bug report to file
        with open(f"{self.res_dir_path}/bug_report_{self.state.total_bug_count-1}.json", "w") as f:
            json.dump(bug_report.__dict__, f, indent=2)
        
        return

    def verify_violations(self) -> None:
        """
        Third phase: verify identified violations with more in-depth analysis
        """
        self.logger.print_log("Starting verification of violations")
        
        # For each potential violation, perform deeper analysis
        potential_violations = []
        
        # Collect all cross-function violations
        for start, ends in self.state.cross_function_violations.items():
            assumption, _ = start
            for end in ends:
                violation, _ = end
                potential_violations.append((assumption, violation))
        
        # Verify each potential violation
        verified_count = 0
        with ThreadPoolExecutor(max_workers=self.max_neural_workers) as executor:
            futures = {}
            for assumption, violation in potential_violations:
                futures[executor.submit(self.__verify_violation, assumption, violation)] = (assumption, violation)
            
            # Collect results
            for future in as_completed(futures):
                assumption, violation = futures[future]
                try:
                    is_verified = future.result()
                    if is_verified:
                        violation_id = f"violation_{verified_count}"
                        self.state.update_verified_violations(violation_id, [assumption, violation])
                        verified_count += 1
                except Exception as e:
                    self.logger.print_log(f"Error verifying violation: {str(e)}")
        
        self.logger.print_log(f"Completed verification of violations. Verified {verified_count} violations.")
        return

    def __verify_violation(self, assumption: Value, violation: Value) -> bool:
        """
        Verify a potential violation with deeper analysis
        """
        # Get functions containing assumption and violation
        function_with_assumption = self.ts_analyzer.function_env[assumption.function_id]
        function_with_violation = self.ts_analyzer.function_env[violation.function_id]
        
        # Get function code
        assumption_code = self.__get_function_code(function_with_assumption)
        violation_code = self.__get_function_code(function_with_violation)
        
        if not assumption_code or not violation_code:
            return False
        
        # Use LLM for deeper verification
        is_verified = self.violation_analyzer.verify_violation(
            function_with_assumption, 
            assumption_code,
            assumption,
            function_with_violation,
            violation_code,
            violation
        )
        
        return is_verified

    def start_scan(self) -> None:
        """
        Main entry point to start the incorrectness logic scan
        """
        self.logger.print_log("Starting incorrectness logic scan")
        
        # Phase 1: Identify assumptions and assertions
        self.identify_assumptions_and_assertions()
        
        # Phase 2: Analyze cross-function violations
        self.analyze_cross_function_violations()
        
        # Phase 3: Verify violations
        self.verify_violations()
        
        # Print summary
        self.logger.print_log(f"Scan complete. Found {self.state.total_bug_count} potential bugs.")
        
        # Save final state for debugging
        with open(f"{self.res_dir_path}/final_state.json", "w") as f:
            # Can't directly dump self.state, so create a simplified representation
            state_dict = {
                "assumption_count": sum(len(v) for v in self.state.assumption_points.values()),
                "potential_violations_count": len(self.state.potential_violations),
                "verified_violations_count": sum(len(paths) for paths in self.state.verified_violations.values()),
                "bug_count": self.state.total_bug_count
            }
            json.dump(state_dict, f, indent=2)
        
        return

    def get_agent_state(self) -> IncorrectnessState:
        return self.state

    def get_log_files(self) -> List[str]:
        return [f for f in os.listdir(self.log_dir_path) if f.endswith(".log")] 