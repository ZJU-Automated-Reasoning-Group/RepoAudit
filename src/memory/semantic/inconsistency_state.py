from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.report.bug_report import *
from memory.semantic.state import *
from tstool.analyzer.TS_analyzer import *
from typing import List, Tuple, Dict, Set


class InconsistencyState(State):
    def __init__(self, assertion_points: List[Value], potential_violations: List[Value]) -> None:
        self.assertion_points = assertion_points
        self.potential_violations = potential_violations
        
        # Track program points with assumptions that could be violated
        self.assumption_points: Dict[str, List[Value]] = {}
        
        # Track violation paths from assumption to potential violation
        self.violation_paths: Dict[Tuple[Value, CallContext], List[Set[Tuple[Value, CallContext]]]] = {}
        
        # Track inter-procedural violations
        self.cross_function_violations: Dict[Tuple[Value, CallContext], Set[Tuple[Value, CallContext]]] = {}
        
        # Track verified violations after analysis
        self.verified_violations: Dict[str, List[Value]] = {}
        
        # Collect bug reports
        self.bug_reports: Dict[int, List[BugReport]] = {}
        self.total_bug_count = 0
        return
    
    def update_assumption_points(self, function_id: str, assumption: Value) -> None:
        """
        Add a program point where an assumption is made
        """
        if function_id not in self.assumption_points:
            self.assumption_points[function_id] = []
        self.assumption_points[function_id].append(assumption)
        return
    
    def update_violation_paths(
        self, start: Tuple[Value, CallContext], ends: Set[Tuple[Value, CallContext]]
    ) -> None:
        """
        Update the violation paths from assumption to potential violation
        """
        if start not in self.violation_paths:
            self.violation_paths[start] = []
        self.violation_paths[start].append(ends)
        return
    
    def update_cross_function_violations(
        self,
        external_start: Tuple[Value, CallContext],
        external_ends: Set[Tuple[Value, CallContext]],
    ) -> None:
        """
        Update inter-procedural violations
        """
        if external_start not in self.cross_function_violations:
            self.cross_function_violations[external_start] = set()
        self.cross_function_violations[external_start].update(external_ends)
        return
    
    def update_verified_violations(self, violation_id: str, path: List[Value]) -> None:
        """
        Add a verified violation path
        """
        if violation_id not in self.verified_violations:
            self.verified_violations[violation_id] = []
        self.verified_violations[violation_id].append(path)
        return
    
    def update_bug_report(self, bug_report: BugReport) -> None:
        """
        Update the bug scan state with the bug report
        :param bug_report: the bug report
        """
        self.bug_reports[self.total_bug_count] = bug_report
        self.total_bug_count += 1
        return
    
    def print_violation_paths(self) -> None:
        """
        Print all violation paths
        """
        print("=====================================")
        print("Violation Paths:")
        print("=====================================")
        for (start_value, start_context), ends in self.violation_paths.items():
            print("-------------------------------------")
            print(f"Assumption: {str(start_value)}, {str(start_context)}")
            for i in range(len(ends)):
                print("--------------------------")
                print(f"  Path {i + 1}:")
                for value, ctx in ends[i]:
                    print(f"  Violation: {value}, {str(ctx)}")
                print("--------------------------")
            print("-------------------------------------")
        print("=====================================\n")
        return
    
    def print_cross_function_violations(self) -> None:
        """
        Print cross-function violations
        """
        print("=====================================")
        print("Cross-Function Violations:")
        print("=====================================")
        for start, ends in self.cross_function_violations.items():
            print("-------------------------------------")
            print(f"Start: {start[0]}, {str(start[1])}")
            for end in ends:
                print(f"  End: {end[0]}, {str(end[1])}")
            print("-------------------------------------")
        print("=====================================\n")
        return
    
    def print_verified_violations(self) -> None:
        """
        Print verified violations
        """
        print("=====================================")
        print("Verified Violations:")
        print("=====================================")
        for violation_id, paths in self.verified_violations.items():
            print("-------------------------------------")
            print(f"Violation ID: {violation_id}")
            for path in paths:
                print(f"  Path: {path}")
            print("-------------------------------------")
        print("=====================================\n")
        return 