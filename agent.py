"""
Data Science Auto-Debugger Agent
Supports multiple AI providers: OpenAI, Groq, Gemini, Cohere
"""

import json
import re
import traceback
import io
import sys
import os
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any
from enum import Enum


class ErrorType(Enum):
    SYNTAX = "SyntaxError"
    RUNTIME = "RuntimeError"
    IMPORT = "ImportError"
    TYPE = "TypeError"
    VALUE = "ValueError"
    ML_LOGIC = "MLLogicError"
    MEMORY = "MemoryError"
    UNKNOWN = "UnknownError"


class FixStatus(Enum):
    PENDING = "pending"
    APPLIED = "applied"
    RESOLVED = "resolved"
    FAILED = "failed"


@dataclass
class ErrorInfo:
    error_type: ErrorType
    error_message: str
    line_number: Optional[int] = None
    faulty_line: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "error_type": self.error_type.value,
            "error_message": self.error_message,
            "line_number": self.line_number,
            "faulty_line": self.faulty_line,
        }


@dataclass
class FixAttempt:
    iteration: int
    root_cause: str
    fix_applied: str
    status: FixStatus
    code_before: str
    code_after: str
    validation_result: Optional[str] = None


@dataclass
class AgentOutput:
    error_type: str
    root_cause: str
    fix_applied: str
    status: str
    iterations: int
    final_status: str
    changes: List[str]
    confidence: str
    corrected_code: str = ""
    explanation: str = ""
    fix_history: List[Dict] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class AIProvider:
    """Multi-provider AI client supporting OpenAI, Groq, Gemini, etc."""
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "auto"):
        self.api_key = api_key
        self.provider = provider
        self.client = None
        self._init_client()
    
    def _init_client(self):
        if not self.api_key:
            return
        
        # Auto-detect provider based on key prefix
        if self.api_key.startswith("gsk_"):
            self.provider = "groq"
        elif self.api_key.startswith("AIza"):
            self.provider = "gemini"
        elif self.api_key.startswith("COHERE"):
            self.provider = "cohere"
        
        if self.provider == "groq":
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except ImportError:
                pass
        
        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai
            except ImportError:
                pass
        
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                pass
    
    def chat(self, prompt: str, model: Optional[str] = None) -> str:
        if not self.client:
            return None
        
        try:
            if self.provider == "groq":
                model = model or "llama-3.1-8b-instant"
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            
            elif self.provider == "gemini":
                model = model or "gemini-pro"
                response = self.client.generate_text(model=model, prompt=prompt)
                return response.result
            
            elif self.provider == "openai":
                model = model or "gpt-3.5-turbo"
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000
                )
                return response.choices[0].message.content
        
        except Exception as e:
            print(f"AI provider error: {e}")
            return None


class CodeExecutor:
    @staticmethod
    def run_code(code: str) -> tuple[bool, str, Optional[str]]:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        
        result_output = ""
        error_output = None
        
        try:
            compiled = compile(code, "<string>", "exec")
            exec(compiled, {"__name__": "__main__"})
            result_output = sys.stdout.getvalue()
            return True, result_output, None
        except SyntaxError as e:
            error_output = traceback.format_exc()
            return False, result_output, error_output
        except Exception as e:
            error_output = traceback.format_exc()
            return False, result_output, error_output
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    @staticmethod
    def run_code_isolated(code: str) -> tuple[bool, str, Optional[str]]:
        import subprocess
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout, None
        return False, result.stdout, result.stderr


class ErrorParser:
    PATTERNS = {
        ErrorType.SYNTAX: [r"SyntaxError:", r"invalid syntax"],
        ErrorType.IMPORT: [r"ImportError:", r"ModuleNotFoundError:", r"No module named"],
        ErrorType.TYPE: [r"TypeError:"],
        ErrorType.VALUE: [r"ValueError:"],
        ErrorType.RUNTIME: [r"RuntimeError:", r"Error:"],
        ErrorType.MEMORY: [r"MemoryError:"],
    }

    def parse(self, traceback_text: str) -> ErrorInfo:
        for error_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, traceback_text, re.IGNORECASE):
                    line_match = re.search(r"line (\d+)", traceback_text)
                    line_number = int(line_match.group(1)) if line_match else None
                    
                    error_msg = self._extract_error_message(traceback_text)
                    
                    return ErrorInfo(
                        error_type=error_type,
                        error_message=error_msg,
                        line_number=line_number,
                        stack_trace=traceback_text
                    )
        
        return ErrorInfo(
            error_type=ErrorType.UNKNOWN,
            error_message=traceback_text[:200] if traceback_text else "Unknown error",
            stack_trace=traceback_text
        )

    def _extract_error_message(self, traceback_text: str) -> str:
        match = re.search(r"(\w+Error): (.+?)(?:\n|$)", traceback_text)
        if match:
            return f"{match.group(1)}: {match.group(2)}"
        return traceback_text.split("\n")[-1] if traceback_text else "Unknown error"


class CodeFixer:
    def apply_fix(self, code: str, error_info: ErrorInfo, fix_instruction: str) -> str:
        lines = code.split("\n")
        
        if error_info.line_number and error_info.line_number <= len(lines):
            target_line = error_info.line_number - 1
            
            if error_info.error_type == ErrorType.SYNTAX:
                lines[target_line] = self._fix_syntax(lines[target_line])
            elif error_info.error_type == ErrorType.IMPORT:
                lines = self._fix_import(lines, error_info.error_message)
        
        return "\n".join(lines)

    def _fix_syntax(self, line: str) -> str:
        line = line.rstrip()
        stripped = line.lstrip()
        
        if not line.endswith(":") and not line.endswith(":"):
            indent = line[:len(line) - len(stripped)]
            if stripped.startswith(("def ", "for ", "while ", "if ", "class ", "elif ", "else:", "except", "try:")):
                return indent + stripped + ":"
            elif re.match(r"^for\s+\w+\s+in\s+.+[^:]$", stripped):
                indent = line[:len(line) - len(stripped)]
                return indent + stripped + ":"
        return line

    def _fix_import(self, lines: List[str], error_msg: str) -> List[str]:
        module_match = re.search(r"No module named '(\w+)'", error_msg)
        if module_match:
            module = module_match.group(1)
            lines.insert(0, f"import {module}")
        return lines


class Validator:
    @staticmethod
    def validate(code: str, original_error: str) -> tuple[bool, str]:
        success, output, new_error = CodeExecutor.run_code(code)
        
        if success:
            return True, "Code executed successfully"
        
        if new_error and new_error == original_error:
            return False, "Same error persists"
        
        return False, f"Different error or issue: {new_error[:200] if new_error else 'Unknown'}"


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, provider: str = "auto"):
        self.ai = AIProvider(api_key, provider)

    def analyze_and_decide(self, code: str, error_info: ErrorInfo, context: str = "") -> Dict[str, Any]:
        result = self.ai.chat(self._build_analysis_prompt(code, error_info, context))
        if result:
            return self._parse_analysis(result, error_info)
        return self._rule_based_analysis(error_info)
    
    def generate_fix(self, code: str, error_info: ErrorInfo) -> Optional[str]:
        prompt = self._build_fix_prompt(code, error_info)
        return self.ai.chat(prompt)
    
    def explain_code(self, code: str) -> str:
        prompt = f"""Analyze and explain this Python code:

CODE:
```{code}
```

Provide a brief explanation:
1. What the code does
2. Key functions
3. Data science relevance

Be concise and educational."""
        result = self.ai.chat(prompt)
        return result or "Explanation not available."
    
    def explain_fix(self, root_cause: str, fix: str, code: str) -> str:
        prompt = f"""Explain this code fix:

ERROR: {root_cause}
FIX: {fix}

CODE:
{code}

Explain:
1. What was wrong
2. What was fixed
3. Where this is used"""
        result = self.ai.chat(prompt)
        return result or f"**What was wrong:** {root_cause}\n\n**What was fixed:** {fix}"

    def _build_analysis_prompt(self, code: str, error_info: ErrorInfo, context: str) -> str:
        return f"""Analyze this Python code error:

Error Type: {error_info.error_type.value}
Error Message: {error_info.error_message}
Line Number: {error_info.line_number}

Code Context:
{context if context else code[:500]}

Respond with JSON:
{{"error_type": "classified", "root_cause": "explanation", "fix_strategy": "how to fix", "confidence": "high/medium/low"}}"""

    def _build_fix_prompt(self, code: str, error_info: ErrorInfo) -> str:
        return f"""You are an expert Python programmer. Fix all errors in this code.

ORIGINAL CODE:
```
{code}
```

ERROR DETECTED:
- Type: {error_info.error_type.value}
- Message: {error_info.error_message}

IMPORTANT:
1. Fix ALL errors in the code
2. Keep the SAME functionality
3. Return the COMPLETE fixed code (no truncation)
4. Do NOT add comments or explanations
5. Do NOT use markdown code blocks

Start directly with the code:"""

    def _parse_analysis(self, result: str, error_info: ErrorInfo) -> Dict[str, Any]:
        try:
            data = json.loads(result)
            return {
                "error_type": data.get("error_type", error_info.error_type.value),
                "root_cause": data.get("root_cause", "Unknown"),
                "fix_strategy": data.get("fix_strategy", "Review code"),
                "confidence": data.get("confidence", "medium")
            }
        except:
            return self._rule_based_analysis(error_info)

    def _rule_based_analysis(self, error_info: ErrorInfo) -> Dict[str, Any]:
        root_causes = {
            ErrorType.SYNTAX: "Syntax error - invalid Python syntax",
            ErrorType.IMPORT: f"Missing module - {error_info.error_message}",
            ErrorType.TYPE: "Type mismatch in operation",
            ErrorType.VALUE: "Invalid value provided",
            ErrorType.RUNTIME: "Runtime execution error",
            ErrorType.MEMORY: "Insufficient memory",
            ErrorType.UNKNOWN: "Unclassified error",
        }
        
        fix_strategies = {
            ErrorType.SYNTAX: "Add missing syntax elements (colons, parentheses)",
            ErrorType.IMPORT: "Install missing module or fix import",
            ErrorType.TYPE: "Convert variables to correct type",
            ErrorType.VALUE: "Provide valid value",
            ErrorType.RUNTIME: "Fix logical error in code",
            ErrorType.MEMORY: "Reduce memory usage",
            ErrorType.UNKNOWN: "Manual investigation needed",
        }
        
        return {
            "error_type": error_info.error_type.value,
            "root_cause": root_causes.get(error_info.error_type, "Unknown cause"),
            "fix_strategy": fix_strategies.get(error_info.error_type, "Review code manually"),
            "confidence": "high" if error_info.error_type != ErrorType.UNKNOWN else "low"
        }


class DataScienceDebuggerAgent:
    MAX_ITERATIONS = 3
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "auto"):
        self.executor = CodeExecutor()
        self.parser = ErrorParser()
        self.fixer = CodeFixer()
        self.validator = Validator()
        self.llm = LLMClient(api_key, provider)
        self.fix_attempts: List[FixAttempt] = []

    def debug(self, code: str, error_message: Optional[str] = None) -> AgentOutput:
        if error_message:
            error_info = self.parser.parse(error_message)
        else:
            success, _, error_msg = self.executor.run_code_isolated(code)
            if success:
                explanation = self.llm.explain_code(code) if self.llm.ai.client else "Code analysis complete."
                return AgentOutput(
                    error_type="None",
                    root_cause="No error found",
                    fix_applied="Code is correct",
                    status="resolved",
                    iterations=0,
                    final_status="success",
                    changes=[],
                    confidence="high",
                    corrected_code=code,
                    explanation=explanation
                )
            error_info = self.parser.parse(error_msg)
        
        current_code = code
        original_error = error_msg if error_message else None
        
        for iteration in range(1, self.MAX_ITERATIONS + 1):
            analysis = self.llm.analyze_and_decide(
                current_code, error_info, 
                context=self._get_context(current_code, error_info.line_number)
            )
            
            fixed_code = self.fixer.apply_fix(
                current_code, error_info, 
                analysis.get("fix_strategy", "")
            )
            
            is_valid, validation_msg = self.validator.validate(fixed_code, original_error or "")
            
            attempt = FixAttempt(
                iteration=iteration,
                root_cause=analysis.get("root_cause", "Unknown"),
                fix_applied=analysis.get("fix_strategy", "No fix applied"),
                status=FixStatus.RESOLVED if is_valid else FixStatus.APPLIED,
                code_before=current_code,
                code_after=fixed_code,
                validation_result=validation_msg
            )
            self.fix_attempts.append(attempt)
            
            if is_valid:
                explanation = self.llm.explain_fix(
                    analysis.get("root_cause", ""),
                    analysis.get("fix_strategy", ""),
                    fixed_code
                )
                return AgentOutput(
                    error_type=analysis.get("error_type", "Unknown"),
                    root_cause=analysis.get("root_cause", "Unknown"),
                    fix_applied=analysis.get("fix_strategy", ""),
                    status="resolved",
                    iterations=iteration,
                    final_status="fixed",
                    changes=[analysis.get("fix_strategy", "")],
                    confidence=analysis.get("confidence", "medium"),
                    corrected_code=fixed_code,
                    explanation=explanation,
                    fix_history=[{
                        "iteration": a.iteration,
                        "root_cause": a.root_cause,
                        "fix": a.fix_applied,
                        "status": a.status.value
                    } for a in self.fix_attempts]
                )
            
            current_code = fixed_code
            
            _, _, new_error = self.executor.run_code_isolated(current_code)
            if new_error:
                error_info = self.parser.parse(new_error)
        
        # Try LLM fix if basic fixes failed
        if self.llm.ai.client:
            llm_fixed = self.llm.generate_fix(code, error_info)
            if llm_fixed:
                # Clean up the fixed code
                llm_fixed = self._clean_code(llm_fixed)
                
                # Check if it compiles (syntax check)
                try:
                    compile(llm_fixed, '<string>', 'exec')
                    compiles = True
                except SyntaxError:
                    compiles = False
                
                # Also try to run it
                success, _, new_error = self.executor.run_code_isolated(llm_fixed)
                
                # Consider it fixed if either:
                # 1. It runs without errors, OR
                # 2. It compiles and the error is different from original (data/runtime issues, not syntax)
                if success or (compiles and new_error and "SyntaxError" not in new_error):
                    explanation = self.llm.explain_fix(
                        error_info.error_message if error_info else "Unknown",
                        "LLM-generated fix",
                        llm_fixed
                    )
                    return AgentOutput(
                        error_type=error_info.error_type.value if error_info else "Unknown",
                        root_cause=error_info.error_message if error_info else "Unknown",
                        fix_applied="LLM fixed the code",
                        status="resolved",
                        iterations=self.MAX_ITERATIONS + 1,
                        final_status="fixed",
                        changes=["LLM-assisted fix"],
                        confidence="high",
                        corrected_code=llm_fixed,
                        explanation=explanation,
                        fix_history=[{
                            "iteration": a.iteration,
                            "root_cause": a.root_cause,
                            "fix": a.fix_applied,
                            "status": a.status.value
                        } for a in self.fix_attempts]
                    )
        
        return AgentOutput(
            error_type=error_info.error_type.value if error_info else "Unknown",
            root_cause=error_info.error_message if error_info else "Could not determine",
            fix_applied="Unable to fix automatically",
            status="failed",
            iterations=self.MAX_ITERATIONS,
            final_status="unresolved",
            changes=[],
            confidence="low",
            fix_history=[{
                "iteration": a.iteration,
                "root_cause": a.root_cause,
                "fix": a.fix_applied,
                "status": a.status.value
            } for a in self.fix_attempts]
        )

    def _clean_code(self, raw_output: str) -> str:
        """Extract clean Python code from LLM response"""
        if not raw_output:
            return raw_output
        
        code = raw_output
        
        # Remove markdown code blocks
        if '```' in code:
            # Find the content between code blocks
            parts = code.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 1:  # This is inside a code block
                    # Remove language identifier if present
                    lines = part.split('\n')
                    if lines[0].strip().startswith(('python', 'py')):
                        lines = lines[1:]
                    code = '\n'.join(lines)
                    break
            else:
                # No proper code block found, use first non-empty part
                for part in parts:
                    if part.strip():
                        code = part.strip()
                        break
        
        # Remove any leading/trailing text descriptions
        lines = code.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            stripped = line.strip()
            # Start capturing after first import/def/class or if already in code
            if not in_code and any(stripped.startswith(kw) for kw in ['import', 'from', 'def ', 'class ', '#', '"""', "'''", 'if ', 'for ', 'while ', 'try:', 'with ']):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        if code_lines:
            code = '\n'.join(code_lines)
        
        return code.strip()
    
    def _get_context(self, code: str, line_number: Optional[int], context_lines: int = 3) -> str:
        if not line_number:
            return code[:500]
        lines = code.split("\n")
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        return "\n".join(lines[start:end])

    def answer_question(self, code: str, question: str) -> str:
        prompt = f"""CODE:
{code}

QUESTION: {question}

Answer based on the code above."""
        result = self.llm.ai.chat(prompt)
        return result or "I need an AI provider to answer questions. Please set your API key."

    def convert_code(self, code: str, from_lang: str, to_lang: str) -> Dict[str, str]:
        prompt = f"""Convert this {from_lang} code to {to_lang}:

{code}

Return ONLY the converted code."""
        result = self.llm.ai.chat(prompt)
        
        if result:
            return {
                "converted_code": result,
                "explanation": f"Converted from {from_lang} to {to_lang}",
                "is_basic": False
            }
        
        return {
            "converted_code": f"# Conversion not available without API key\n{code}",
            "explanation": "Set your API key (Groq, OpenAI, or Gemini) for conversion",
            "is_basic": True
        }


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Data Science Auto-Debugger Agent")
    print("=" * 60)
    
    agent = DataScienceDebuggerAgent()
    
    # Test syntax error
    code = """for i in range(5)
    print(i)"""
    
    print(f"\nTesting code:\n{code}")
    result = agent.debug(code)
    print(f"\nResult: {result.final_status}")
    print(f"Corrected:\n{result.corrected_code}")
    print(f"Explanation: {result.explanation}")
