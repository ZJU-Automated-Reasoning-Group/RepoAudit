#!/usr/bin/env python3
"""
LLM x 漏洞挖掘 - 内存安全漏洞静态审计系统
单一漏洞类型检测，多模型协同判断
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
BASE_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_PATH / "src"))

import json
import time
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from llmtool.LLM_tool import LLMTool, LLMToolInput, LLMToolOutput
from ui.logger import Logger


class VulnType(Enum):
    NPD = "Null Pointer Dereference"
    UAF = "Use-After-Free"
    BOF = "Buffer Overflow"
    ML = "Memory Leak"


class Severity(Enum):
    CRITICAL = "严重"
    HIGH = "高危"
    MEDIUM = "中危"
    LOW = "低危"


@dataclass
class Finding:
    vuln_type: VulnType
    severity: Severity
    description: str
    line_range: str
    confidence: float
    agent_id: str


class MemoryAuditInput(LLMToolInput):
    def __init__(self, code: str, bug_type: VulnType, language: str = "C"):
        self.code = code
        self.bug_type = bug_type
        self.language = language
    
    def __hash__(self):
        return hash((self.code, self.bug_type.name, self.language))


class MemoryAuditOutput(LLMToolOutput):
    def __init__(self, findings: List[Finding]):
        self.findings = findings


class VulnerabilityAnalyzer(LLMTool):
    """通用漏洞分析工具"""
    def __init__(self, model_name: str, agent_id: str, temperature: float, language: str, max_query_num: int, logger: Logger):
        super().__init__(model_name, temperature, language, max_query_num, logger)
        self.agent_id = agent_id
    
    def _get_prompt(self, input: MemoryAuditInput) -> str:
        bug_descriptions = {
            VulnType.NPD: "空指针解引用 - 访问NULL指针",
            VulnType.UAF: "释放后使用 - 使用已释放的内存",
            VulnType.BOF: "缓冲区溢出 - 写入超出缓冲区边界",
            VulnType.ML: "内存泄漏 - 分配的内存未释放"
        }
        
        return f"""你是安全专家，需要检查{input.language}代码中的{bug_descriptions[input.bug_type]}漏洞。

代码：
```{input.language}
{input.code}
```

请仔细分析代码，只关注{input.bug_type.value}类型的漏洞。

返回JSON格式：
{{
    "findings": [
        {{
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "description": "详细描述发现的问题",
            "line_range": "L1-L3",
            "confidence": 0.85
        }}
    ]
}}

如果没有发现问题，返回空数组。只返回JSON，不要其他内容。"""

    def _parse_response(self, response: str, input: MemoryAuditInput = None) -> MemoryAuditOutput:
        try:
            # Clean the response to extract JSON
            response = response.strip()
            
            # Remove code block markers if present
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end]
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end]
            
            response = response.strip()
            
            # Skip empty responses
            if not response:
                return MemoryAuditOutput([])
            
            # Parse JSON
            data = json.loads(response)
            findings = []
            
            for item in data.get("findings", []):
                finding = Finding(
                    vuln_type=input.bug_type,
                    severity=Severity[item["severity"]],
                    description=item["description"],
                    line_range=item["line_range"],
                    confidence=item["confidence"],
                    agent_id=self.agent_id
                )
                findings.append(finding)
            return MemoryAuditOutput(findings)
        except Exception as e:
            self.logger.print_log(f"Error parsing {self.agent_id} response: {e}")
            self.logger.print_log(f"Raw response: {response}")
            return MemoryAuditOutput([])


class MemoryAuditor:
    def __init__(self, bug_type: VulnType, language: str = "C", temperature: float = 0.0):
        self.bug_type = bug_type
        self.language = language
        self.temperature = temperature
        
        # Initialize logger
        log_dir = f"{BASE_PATH}/log/swarm_audit/{bug_type.name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        os.makedirs(log_dir, exist_ok=True)
        self.logger = Logger(f"{log_dir}/audit.log")
        
        # Initialize multiple models for the same bug type
        self.agents = [
            ("glm-4-flash", "安全专家"),
            ("glm-4-flash", "静态分析专家"),
            ("glm-4-flash", "资深程序员")
        ]
    
    def judge(self, all_findings: List[Finding]) -> List[Finding]:
        """综合判断 - 至少2个模型同意才确认"""
        if len(all_findings) < 2:
            return []
        
        # 按位置分组
        grouped = {}
        for f in all_findings:
            key = f.line_range
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(f)
        
        final_findings = []
        for line_range, findings in grouped.items():
            if len(findings) >= 2:  # 至少2个模型检测到
                avg_confidence = sum(f.confidence for f in findings) / len(findings)
                max_severity = max(findings, key=lambda x: list(Severity).index(x.severity)).severity
                
                final_findings.append(Finding(
                    vuln_type=self.bug_type,
                    severity=max_severity,
                    description=f"多模型确认：{findings[0].description}",
                    line_range=line_range,
                    confidence=min(0.99, avg_confidence + 0.1),
                    agent_id="Judge"
                ))
        
        return final_findings
    
    def analyze(self, code: str) -> Dict:
        """分析代码"""
        self.logger.print_console(f"🔍 开始{self.bug_type.value}检测...\n")
        
        audit_input = MemoryAuditInput(code, self.bug_type, self.language)
        all_findings = []
        
        # 并行调用多个模型
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            futures = {}
            for model_name, agent_name in self.agents:
                analyzer = VulnerabilityAnalyzer(
                    model_name, agent_name, self.temperature, 
                    self.language, 5, self.logger
                )
                futures[executor.submit(analyzer.invoke, audit_input)] = agent_name
            
            for future in as_completed(futures):
                agent_name = futures[future]
                try:
                    output = future.result()
                    if output and output.findings:
                        all_findings.extend(output.findings)
                        self.logger.print_console(f"✅ {agent_name} 发现{len(output.findings)}个问题")
                    else:
                        self.logger.print_console(f"✅ {agent_name} 未发现问题")
                except Exception as e:
                    self.logger.print_log(f"Error in {agent_name}: {e}")
                    self.logger.print_console(f"❌ {agent_name} 执行失败")
        
        # 综合判断
        final_findings = self.judge(all_findings)
        
        return {
            "bug_type": self.bug_type.value,
            "total_findings": len(all_findings),
            "confirmed_findings": final_findings
        }

def main():
    # 示例：检测UAF漏洞
    code = """
    void example() {
        char *ptr = malloc(100);
        *ptr = 'A';
        free(ptr);
        *ptr = 'B';  // UAF here
    }
    """
    
    auditor = MemoryAuditor(VulnType.UAF)
    report = auditor.analyze(code)
    
    print(f"\n📊 {report['bug_type']}检测完成")
    print(f"📋 发现{report['total_findings']}个初步问题，确认{len(report['confirmed_findings'])}个\n")
    
    for f in report['confirmed_findings']:
        print(f"[{f.severity.value}] {f.description}")
        print(f"  位置: {f.line_range}, 置信度: {f.confidence:.1%}\n")

if __name__ == "__main__":
    main()
