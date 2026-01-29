"""
Guardrails Module
=================

Provides safety mechanisms for LLM interactions:
- Input validation (prompt injection protection, length limits)
- Output validation (code safety checks, format validation)
- Content filtering (harmful content detection)
- Rate limiting logic

WHY GUARDRAILS?
    LLMs can be manipulated or produce harmful outputs.
    Guardrails act as a safety layer:

    User Input → [GUARDRAILS] → LLM → [GUARDRAILS] → Output
                     ↓                      ↓
              Validate/Sanitize       Validate/Filter

COMPONENTS:

1. INPUT GUARDRAILS:
   - Prompt injection detection
   - Input length limits
   - Content policy checks
   - PII detection

2. OUTPUT GUARDRAILS:
   - Code safety validation
   - Format verification
   - Sensitive data filtering
   - Response quality checks

DATA FLOW:
    ┌─────────────────────────────────────────────────────────────┐
    │                   INPUT GUARDRAILS                           │
    │                                                              │
    │  User Input                                                  │
    │      ↓                                                       │
    │  ┌─────────────────┐                                        │
    │  │ Length Check    │ ─ Too long? → Truncate/Reject          │
    │  └────────┬────────┘                                        │
    │           ↓                                                  │
    │  ┌─────────────────┐                                        │
    │  │ Injection Check │ ─ Suspicious? → Flag/Reject            │
    │  └────────┬────────┘                                        │
    │           ↓                                                  │
    │  ┌─────────────────┐                                        │
    │  │ Content Policy  │ ─ Harmful? → Reject with message       │
    │  └────────┬────────┘                                        │
    │           ↓                                                  │
    │      Validated Input → LLM                                  │
    └─────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │                  OUTPUT GUARDRAILS                           │
    │                                                              │
    │  LLM Response                                                │
    │      ↓                                                       │
    │  ┌─────────────────┐                                        │
    │  │ Code Safety     │ ─ Dangerous code? → Remove/Warn        │
    │  └────────┬────────┘                                        │
    │           ↓                                                  │
    │  ┌─────────────────┐                                        │
    │  │ Format Check    │ ─ Malformed? → Attempt fix             │
    │  └────────┬────────┘                                        │
    │           ↓                                                  │
    │  ┌─────────────────┐                                        │
    │  │ PII Filter      │ ─ Contains PII? → Redact               │
    │  └────────┬────────┘                                        │
    │           ↓                                                  │
    │      Safe Output → User                                     │
    └─────────────────────────────────────────────────────────────┘

USAGE:
    from src.services.guardrails import Guardrails, GuardrailConfig

    guardrails = Guardrails(GuardrailConfig(
        max_input_length=10000,
        enable_injection_check=True,
        enable_code_safety=True
    ))

    # Validate input
    result = guardrails.validate_input(user_prompt)
    if not result.is_valid:
        return error_response(result.message)

    # Validate output
    safe_output = guardrails.validate_output(llm_response)
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.logging import LoggerMixin


class GuardrailAction(Enum):
    """Action to take when guardrail is triggered."""
    ALLOW = "allow"          # Let it through
    WARN = "warn"            # Allow but log warning
    MODIFY = "modify"        # Modify the content
    REJECT = "reject"        # Block entirely


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GuardrailResult:
    """
    Result from a guardrail check.

    Attributes:
        is_valid: Whether input/output passed the check
        action: Recommended action
        risk_level: Assessed risk level
        message: Human-readable message
        modified_content: Modified content (if action is MODIFY)
        violations: List of specific violations found
        metadata: Additional information
    """
    is_valid: bool
    action: GuardrailAction
    risk_level: RiskLevel = RiskLevel.LOW
    message: str = ""
    modified_content: str | None = None
    violations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailConfig:
    """
    Configuration for guardrails.

    Attributes:
        max_input_length: Maximum allowed input length
        max_output_length: Maximum allowed output length
        enable_injection_check: Check for prompt injection
        enable_content_policy: Check content policy
        enable_pii_filter: Filter PII from outputs
        enable_code_safety: Check code for dangerous patterns
        blocked_patterns: Additional regex patterns to block
        allowed_code_imports: Whitelist of allowed imports in generated code
    """
    # Length limits
    max_input_length: int = 50000
    max_output_length: int = 100000

    # Feature flags
    enable_injection_check: bool = True
    enable_content_policy: bool = True
    enable_pii_filter: bool = True
    enable_code_safety: bool = True

    # Custom patterns
    blocked_patterns: list[str] = field(default_factory=list)
    allowed_code_imports: list[str] = field(default_factory=lambda: [
        "os", "sys", "re", "json", "typing", "datetime", "collections",
        "itertools", "functools", "pathlib", "dataclasses", "enum",
        "logging", "unittest", "pytest", "asyncio", "aiohttp",
        "requests", "fastapi", "pydantic", "sqlalchemy", "numpy", "pandas"
    ])

    # Thresholds
    injection_score_threshold: float = 0.7
    pii_confidence_threshold: float = 0.8


# ============================================================================
# PROMPT INJECTION DETECTION PATTERNS
# ============================================================================

INJECTION_PATTERNS = [
    # Direct instruction overrides
    r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)",
    r"disregard\s+(previous|all|your)\s+(instructions?|rules?)",
    r"forget\s+(everything|all|previous)",
    r"new\s+instructions?:",
    r"override\s+(system|instructions?)",

    # Role manipulation
    r"you\s+are\s+(now|actually)\s+",
    r"pretend\s+(to\s+be|you('re|'re)|you\s+are)",
    r"act\s+as\s+(if|a)",
    r"simulate\s+(being|a)",
    r"roleplay\s+as",

    # System prompt extraction
    r"(what|show|tell|reveal|display|print)\s+(is|me|are)?\s*(your|the)?\s*(system\s+)?(prompt|instructions)",
    r"repeat\s+(your|the|back)\s+(system\s+)?(prompt|instructions)",

    # Delimiter exploitation
    r"\[SYSTEM\]|\[INST\]|\<\|im_start\|",
    r"###\s*(SYSTEM|USER|ASSISTANT)",
    r"\{\{(system|user|assistant)\}\}",

    # Encoding tricks
    r"base64\s*(decode|encode)",
    r"unicode\s*(escape|decode)",
    r"hex\s*(decode|encode)",
]

# Compiled patterns for efficiency
COMPILED_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS
]


# ============================================================================
# DANGEROUS CODE PATTERNS
# ============================================================================

DANGEROUS_CODE_PATTERNS = [
    # System command execution
    (r"os\.system\s*\(", "System command execution"),
    (r"subprocess\.(run|call|Popen|check_output)\s*\(", "Subprocess execution"),
    (r"exec\s*\(", "Dynamic code execution"),
    (r"eval\s*\(", "Dynamic evaluation"),
    (r"__import__\s*\(", "Dynamic import"),
    (r"compile\s*\(.*,\s*['\"]exec['\"]\s*\)", "Dynamic compilation"),

    # File system operations (without context)
    (r"open\s*\([^)]*['\"]w['\"]", "File write operation"),
    (r"shutil\.(rmtree|remove|move)", "File system modification"),
    (r"os\.(remove|unlink|rmdir)", "File deletion"),

    # Network operations
    (r"socket\.socket\s*\(", "Raw socket creation"),
    (r"urllib\.request\.urlopen\s*\(", "URL fetching"),

    # Credential/secret patterns
    (r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded credential"),

    # Pickle (security risk)
    (r"pickle\.(load|loads)\s*\(", "Pickle deserialization (security risk)"),
]


# ============================================================================
# PII PATTERNS
# ============================================================================

PII_PATTERNS = [
    # Email addresses
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),

    # Phone numbers (various formats)
    (r"\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b", "phone"),

    # SSN
    (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "ssn"),

    # Credit card numbers
    (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "credit_card"),

    # IP addresses
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "ip_address"),

    # API keys (common patterns)
    (r"\b(sk-[a-zA-Z0-9]{32,})\b", "api_key"),
    (r"\b(ghp_[a-zA-Z0-9]{36})\b", "github_token"),
    (r"\b(xox[baprs]-[0-9a-zA-Z-]+)\b", "slack_token"),
]


class Guardrails(LoggerMixin):
    """
    Main guardrails class providing input/output validation.

    This class acts as a safety layer between users and the LLM,
    validating inputs before they reach the model and outputs
    before they reach the user.

    Attributes:
        config: Guardrail configuration
    """

    def __init__(self, config: GuardrailConfig | None = None) -> None:
        """
        Initialize guardrails with configuration.

        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or GuardrailConfig()

        # Compile custom blocked patterns
        self._custom_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.blocked_patterns
        ]

    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================

    def validate_input(self, text: str, context: dict[str, Any] | None = None) -> GuardrailResult:
        """
        Validate user input before sending to LLM.

        Performs multiple checks:
        1. Length validation
        2. Prompt injection detection
        3. Content policy check

        Args:
            text: User input text
            context: Optional context (e.g., user_id, request_type)

        Returns:
            GuardrailResult with validation outcome

        Example:
            result = guardrails.validate_input(user_prompt)
            if not result.is_valid:
                raise ValueError(result.message)
        """
        violations = []
        risk_level = RiskLevel.LOW
        metadata = {"original_length": len(text)}

        # Check 1: Length validation
        if len(text) > self.config.max_input_length:
            self.logger.warning(
                "Input exceeds max length",
                length=len(text),
                max_length=self.config.max_input_length
            )
            return GuardrailResult(
                is_valid=False,
                action=GuardrailAction.REJECT,
                risk_level=RiskLevel.MEDIUM,
                message=f"Input too long. Maximum {self.config.max_input_length} characters allowed.",
                violations=["length_exceeded"],
                metadata=metadata
            )

        # Check 2: Prompt injection detection
        if self.config.enable_injection_check:
            injection_result = self._check_prompt_injection(text)
            if injection_result["detected"]:
                violations.extend(injection_result["patterns"])
                risk_level = RiskLevel.HIGH if injection_result["score"] > 0.5 else RiskLevel.MEDIUM

                if injection_result["score"] >= self.config.injection_score_threshold:
                    self.logger.warning(
                        "Prompt injection detected",
                        score=injection_result["score"],
                        patterns=injection_result["patterns"]
                    )
                    return GuardrailResult(
                        is_valid=False,
                        action=GuardrailAction.REJECT,
                        risk_level=RiskLevel.CRITICAL,
                        message="Your request appears to contain instructions that could manipulate the AI. Please rephrase your question.",
                        violations=violations,
                        metadata={**metadata, "injection_score": injection_result["score"]}
                    )

        # Check 3: Content policy
        if self.config.enable_content_policy:
            policy_result = self._check_content_policy(text)
            if not policy_result["compliant"]:
                violations.extend(policy_result["violations"])
                return GuardrailResult(
                    is_valid=False,
                    action=GuardrailAction.REJECT,
                    risk_level=RiskLevel.HIGH,
                    message=policy_result["message"],
                    violations=violations,
                    metadata=metadata
                )

        # Check 4: Custom blocked patterns
        for pattern in self._custom_patterns:
            if pattern.search(text):
                violations.append(f"blocked_pattern:{pattern.pattern}")

        # Input passed all checks
        return GuardrailResult(
            is_valid=True,
            action=GuardrailAction.ALLOW if not violations else GuardrailAction.WARN,
            risk_level=risk_level,
            message="Input validated successfully",
            violations=violations,
            metadata=metadata
        )

    def _check_prompt_injection(self, text: str) -> dict[str, Any]:
        """
        Check for prompt injection attempts.

        Args:
            text: Input text to check

        Returns:
            Dict with detection results
        """
        detected_patterns = []
        score = 0.0

        text_lower = text.lower()

        for pattern in COMPILED_INJECTION_PATTERNS:
            matches = pattern.findall(text_lower)
            if matches:
                detected_patterns.append(pattern.pattern)
                score += 0.2  # Each pattern match increases score

        # Check for excessive special characters (delimiter abuse)
        special_char_ratio = sum(1 for c in text if c in "[]{}|<>") / max(len(text), 1)
        if special_char_ratio > 0.1:
            detected_patterns.append("excessive_special_chars")
            score += 0.1

        # Normalize score to 0-1
        score = min(score, 1.0)

        return {
            "detected": len(detected_patterns) > 0,
            "score": score,
            "patterns": detected_patterns
        }

    def _check_content_policy(self, text: str) -> dict[str, Any]:
        """
        Check content against policy.

        Args:
            text: Input text

        Returns:
            Policy compliance result
        """
        violations = []

        # Check for harmful content requests
        harmful_patterns = [
            (r"(create|write|generate)\s+(malware|virus|exploit)", "malware_request"),
            (r"(hack|attack|ddos|dos)\s+(into|against)", "attack_request"),
            (r"(steal|extract|exfiltrate)\s+(data|credentials|passwords)", "data_theft"),
        ]

        for pattern, violation_type in harmful_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(violation_type)

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "message": "Your request contains content that violates our usage policy." if violations else ""
        }

    # =========================================================================
    # OUTPUT VALIDATION
    # =========================================================================

    def validate_output(
        self,
        text: str,
        output_type: str = "text",
        context: dict[str, Any] | None = None
    ) -> GuardrailResult:
        """
        Validate LLM output before returning to user.

        Performs multiple checks:
        1. Length validation
        2. Code safety check (if output contains code)
        3. PII filtering

        Args:
            text: LLM output text
            output_type: Type of output ("text", "code", "mixed")
            context: Optional context

        Returns:
            GuardrailResult (may include modified content)

        Example:
            result = guardrails.validate_output(llm_response, output_type="code")
            output = result.modified_content or llm_response
        """
        violations = []
        modified_text = text
        risk_level = RiskLevel.LOW
        metadata = {"output_type": output_type}

        # Check 1: Length
        if len(text) > self.config.max_output_length:
            modified_text = text[:self.config.max_output_length] + "\n\n[Output truncated due to length]"
            violations.append("length_truncated")

        # Check 2: Code safety (if enabled and output contains code)
        if self.config.enable_code_safety and ("```" in text or output_type == "code"):
            code_result = self._check_code_safety(text)
            if code_result["issues"]:
                violations.extend(code_result["issues"])
                risk_level = RiskLevel.MEDIUM
                modified_text = self._add_code_warnings(modified_text, code_result["issues"])
                metadata["code_warnings"] = code_result["issues"]

        # Check 3: PII filtering
        if self.config.enable_pii_filter:
            pii_result = self._filter_pii(modified_text)
            if pii_result["found"]:
                violations.extend([f"pii:{t}" for t in pii_result["types"]])
                modified_text = pii_result["filtered_text"]
                metadata["pii_redacted"] = pii_result["count"]

        action = GuardrailAction.ALLOW
        if modified_text != text:
            action = GuardrailAction.MODIFY
        elif violations:
            action = GuardrailAction.WARN

        return GuardrailResult(
            is_valid=True,  # We allow outputs but may modify them
            action=action,
            risk_level=risk_level,
            message="Output processed successfully",
            modified_content=modified_text if modified_text != text else None,
            violations=violations,
            metadata=metadata
        )

    def _check_code_safety(self, text: str) -> dict[str, Any]:
        """
        Check code in output for dangerous patterns.

        Args:
            text: Text potentially containing code

        Returns:
            Code safety analysis result
        """
        issues = []

        # Extract code blocks
        code_blocks = re.findall(r"```(?:\w*\n)?(.*?)```", text, re.DOTALL)
        code_to_check = "\n".join(code_blocks) if code_blocks else text

        for pattern, description in DANGEROUS_CODE_PATTERNS:
            if re.search(pattern, code_to_check, re.IGNORECASE):
                issues.append(description)

        return {
            "issues": issues,
            "code_blocks_found": len(code_blocks)
        }

    def _add_code_warnings(self, text: str, issues: list[str]) -> str:
        """
        Add warnings to code output.

        Args:
            text: Output text
            issues: List of issues found

        Returns:
            Text with warnings added
        """
        warning = "\n\n⚠️ **Security Notice**: The generated code contains patterns that may require careful review:\n"
        for issue in issues:
            warning += f"- {issue}\n"
        warning += "\nPlease review the code carefully before using it in production.\n"

        return warning + text

    def _filter_pii(self, text: str) -> dict[str, Any]:
        """
        Filter PII from output.

        Args:
            text: Output text

        Returns:
            Filtering result with redacted text
        """
        filtered_text = text
        found_types = []
        count = 0

        for pattern, pii_type in PII_PATTERNS:
            matches = re.findall(pattern, filtered_text)
            if matches:
                found_types.append(pii_type)
                count += len(matches)
                # Redact the PII
                filtered_text = re.sub(pattern, f"[REDACTED-{pii_type.upper()}]", filtered_text)

        return {
            "found": count > 0,
            "types": list(set(found_types)),
            "count": count,
            "filtered_text": filtered_text
        }

    # =========================================================================
    # CODE GENERATION SPECIFIC
    # =========================================================================

    def validate_generated_code(self, code: str, language: str = "python") -> GuardrailResult:
        """
        Validate generated code specifically.

        More thorough checks for code generation outputs.

        Args:
            code: Generated code
            language: Programming language

        Returns:
            Validation result
        """
        violations = []
        modified_code = code

        # Check for dangerous patterns
        safety_result = self._check_code_safety(code)
        violations.extend(safety_result["issues"])

        # Check imports (Python specific)
        if language == "python":
            import_result = self._validate_imports(code)
            violations.extend(import_result["issues"])

        risk_level = RiskLevel.LOW
        if len(violations) >= 3:
            risk_level = RiskLevel.HIGH
        elif len(violations) >= 1:
            risk_level = RiskLevel.MEDIUM

        return GuardrailResult(
            is_valid=len(violations) == 0,
            action=GuardrailAction.WARN if violations else GuardrailAction.ALLOW,
            risk_level=risk_level,
            message="Code validation complete",
            modified_content=modified_code if modified_code != code else None,
            violations=violations,
            metadata={"language": language}
        )

    def _validate_imports(self, code: str) -> dict[str, Any]:
        """
        Validate imports in Python code.

        Args:
            code: Python code

        Returns:
            Import validation result
        """
        issues = []

        # Find all imports
        import_pattern = r"(?:from\s+(\S+)\s+)?import\s+(\S+)"
        imports = re.findall(import_pattern, code)

        # Dangerous import modules
        dangerous_modules = ["ctypes", "cffi", "win32api", "win32con"]

        for from_module, import_name in imports:
            module = from_module or import_name.split(".")[0]
            if module in dangerous_modules:
                issues.append(f"Potentially dangerous import: {module}")

        return {"issues": issues}


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Default guardrails instance
_default_guardrails: Guardrails | None = None


def get_guardrails(config: GuardrailConfig | None = None) -> Guardrails:
    """
    Get or create default guardrails instance.

    Args:
        config: Optional configuration

    Returns:
        Guardrails instance
    """
    global _default_guardrails
    if _default_guardrails is None or config is not None:
        _default_guardrails = Guardrails(config)
    return _default_guardrails


def validate_prompt(text: str) -> GuardrailResult:
    """
    Quick validation of a prompt.

    Args:
        text: Prompt text

    Returns:
        Validation result
    """
    return get_guardrails().validate_input(text)


def validate_response(text: str, output_type: str = "text") -> GuardrailResult:
    """
    Quick validation of a response.

    Args:
        text: Response text
        output_type: Type of output

    Returns:
        Validation result
    """
    return get_guardrails().validate_output(text, output_type)
