import json
from typing import Dict, List, Optional, Tuple

class CWEMapper:
    """Maintains CWE (Common Weakness Enumeration) mappings for querying."""
    
    def __init__(self):
        self.cwe_map = {
            "CWE-20": "Improper Input Validation",
            "CWE-22": "Path Traversal",
            "CWE-77": "Command Injection",
            "CWE-78": "OS Command Injection",
            "CWE-79": "Cross-site Scripting (XSS)",
            "CWE-89": "SQL Injection",
            "CWE-94": "Code Injection",
            "CWE-119": "Buffer Overflow",
            "CWE-125": "Out-of-bounds Read",
            "CWE-200": "Information Exposure",
            "CWE-269": "Improper Privilege Management",
            "CWE-287": "Improper Authentication",
            "CWE-295": "Improper Certificate Validation",
            "CWE-312": "Cleartext Storage of Sensitive Information",
            "CWE-319": "Cleartext Transmission of Sensitive Information",
            "CWE-327": "Broken Cryptographic Algorithm",
            "CWE-352": "Cross-Site Request Forgery (CSRF)",
            "CWE-400": "Uncontrolled Resource Consumption",
            "CWE-434": "Unrestricted File Upload",
            "CWE-476": "NULL Pointer Dereference",
            "CWE-502": "Deserialization of Untrusted Data",
            "CWE-611": "XML External Entity (XXE)",
            "CWE-787": "Out-of-bounds Write",
            "CWE-798": "Hard-coded Credentials",
            "CWE-862": "Missing Authorization",
            "CWE-918": "Server-Side Request Forgery (SSRF)"
        }
    
    def get(self, cwe_id: str) -> Optional[str]:
        """Get CWE description. Accepts 'CWE-89', '89', etc."""
        normalized = f"CWE-{cwe_id}" if cwe_id.isdigit() else cwe_id.upper()
        return self.cwe_map.get(normalized)
    
    def search(self, keyword: str) -> List[Tuple[str, str]]:
        """Search CWEs by keyword in description."""
        keyword_lower = keyword.lower()
        return [(cwe_id, desc) for cwe_id, desc in self.cwe_map.items() 
                if keyword_lower in desc.lower()]
    
    def add(self, cwe_id: str, description: str) -> None:
        """Add or update a CWE mapping."""
        normalized = f"CWE-{cwe_id}" if cwe_id.isdigit() else cwe_id.upper()
        self.cwe_map[normalized] = description
    
    def all(self) -> Dict[str, str]:
        """Get all CWE mappings."""
        return self.cwe_map.copy()
    
    def save(self, filename: str) -> None:
        """Save to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.cwe_map, f, indent=2)
    
    def load(self, filename: str) -> None:
        """Load from JSON file."""
        with open(filename, 'r') as f:
            self.cwe_map.update(json.load(f))


# Quick utility functions
def cwe_lookup(cwe_id: str) -> str:
    """Quick CWE description lookup."""
    mapper = CWEMapper()
    return mapper.get(cwe_id) or f"CWE {cwe_id} not found"

def get_cwe_dict() -> Dict[str, str]:
    """Get basic CWE dictionary."""
    return CWEMapper().all()


# Example usage
if __name__ == "__main__":
    cwe = CWEMapper()
    
    # Basic lookup
    print(cwe.get("89"))  # SQL Injection
    print(cwe.get("CWE-79"))  # Cross-site Scripting (XSS)
    
    # Search
    injection_cwes = cwe.search("injection")
    for cwe_id, desc in injection_cwes:
        print(f"{cwe_id}: {desc}")