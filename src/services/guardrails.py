"""
Guardrails Module (using Guardrails AI)
=======================================

Production-grade LLM safety using the Guardrails AI library.

Provides:
- Input validation (prompt injection, content policy)
- Output validation (code safety, PII filtering, format)
- Configurable validators from Guardrails Hub

GUARDRAILS AI OVERVIEW:
    Guardrails AI is a production library for validating LLM outputs.
    It uses "validators" from the Guardrails Hub that can be composed.

    ┌─────────────────────────────────────────────────────────────────┐
    │                   GUARDRAILS AI FLOW                             │
    │                                                                  │
    │  User Input                                                      │
    │      ↓                                                           │
    │  ┌─────────────────┐                                            │
    │  │ Guard().use()   │  ← Compose validators                      │
    │  │ - DetectPII     │                                            │
    │  │ - ToxicLanguage │                                            │
    │  │ - ValidPython   │                                            │
    │  └────────┬────────┘                                            │
    │           ↓                                                      │
    │  ┌─────────────────┐                                            │
    │  │   Validation    │  ← On fail: fix, reask, exception          │
    │  └────────┬────────┘                                            │
    │           ↓                                                      │
    │      Validated Output                                           │
    └─────────────────────────────────────────────────────────────────┘

VALIDATORS USED:
    From Guardrails Hub (https://hub.guardrailsai.com/):
    - DetectPII: Detects and redacts personal information
    - ToxicLanguage: Detects harmful/toxic content
    - DetectPromptInjection: Detects prompt injection attempts
    - ValidPython: Validates Python code syntax
    - RestrictToTopic: Keeps responses on topic

INSTALLATION:
    pip install guardrails-ai
    guardrails hub install hub://guardrails/detect_pii
    guardrails hub install hub://guardrails/toxic_language
    guardrails hub install hub://guardrails/detect_prompt_injection
    guardrails hub install hub://guardrails/valid_python

USAGE:
    from src.services.guardrails import Guardrails, GuardrailConfig

    guardrails = Guardrails(GuardrailConfig(
        enable_pii_filter=True,
        enable_toxicity_check=True
    ))

    # Validate input
    result = guardrails.validate_input(user_prompt)
    if not result.is_valid:
        return error_response(result.message)

    # Validate output
    result = guardrails.validate_output(llm_response)
    safe_output = result.modified_content or llm_response
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from src.core.logging import LoggerMixin

# Try to import guardrails-ai components
# Fall back to manual validation if not installed
try:
    from guardrails import Guard
    from guardrails.errors import ValidationError as GuardrailsValidationError
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False

# Try to import hub validators
# These need to be installed separately via: guardrails hub install hub://guardrails/<validator>
try:
    from guardrails.hub import DetectPII
    DETECT_PII_AVAILABLE = True
except ImportError:
    DETECT_PII_AVAILABLE = False

try:
    from guardrails.hub import ToxicLanguage
    TOXIC_LANGUAGE_AVAILABLE = True
except ImportError:
    TOXIC_LANGUAGE_AVAILABLE = False

try:
    from guardrails.hub import DetectPromptInjection
    PROMPT_INJECTION_AVAILABLE = True
except ImportError:
    PROMPT_INJECTION_AVAILABLE = False

try:
    from guardrails.hub import ValidPython
    VALID_PYTHON_AVAILABLE = True
except ImportError:
    VALID_PYTHON_AVAILABLE = False


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
        enable_pii_filter: Filter PII from outputs (uses DetectPII)
        enable_toxicity_check: Check for toxic content (uses ToxicLanguage)
        enable_injection_check: Check for prompt injection (uses DetectPromptInjection)
        enable_code_validation: Validate Python code syntax (uses ValidPython)
        enable_content_policy: Check content policy (manual check)
        pii_on_fail: Action when PII detected ("fix", "exception", "noop")
        toxicity_threshold: Threshold for toxic content detection (0-1)
        custom_validators: List of additional custom validator functions
    """
    # Length limits
    max_input_length: int = 50000
    max_output_length: int = 100000

    # Feature flags for Guardrails AI validators
    enable_pii_filter: bool = True
    enable_toxicity_check: bool = True
    enable_injection_check: bool = True
    enable_code_validation: bool = True
    enable_content_policy: bool = True

    # Guardrails AI specific settings
    pii_on_fail: str = "fix"  # "fix" = redact, "exception" = raise, "noop" = pass
    toxicity_threshold: float = 0.8
    toxicity_on_fail: str = "exception"

    # Custom validators (fallback or additional)
    custom_validators: list[Callable] = field(default_factory=list)


# ============================================================================
# FALLBACK PATTERNS (used when Guardrails AI not installed)
# ============================================================================

INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)",
    r"disregard\s+(previous|all|your)\s+(instructions?|rules?)",
    r"forget\s+(everything|all|previous)",
    r"new\s+instructions?:",
    r"you\s+are\s+(now|actually)\s+",
    r"pretend\s+(to\s+be|you('re|'re)|you\s+are)",
    r"(what|show|tell|reveal)\s+(is|me)?\s*(your|the)?\s*(system\s+)?(prompt|instructions)",
]

PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email", "[EMAIL REDACTED]"),
    (r"\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b", "phone", "[PHONE REDACTED]"),
    (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "ssn", "[SSN REDACTED]"),
    (r"\b(sk-[a-zA-Z0-9]{32,})\b", "api_key", "[API_KEY REDACTED]"),
]

DANGEROUS_CODE_PATTERNS = [
    (r"os\.system\s*\(", "System command execution"),
    (r"subprocess\.(run|call|Popen)\s*\(", "Subprocess execution"),
    (r"exec\s*\(", "Dynamic code execution"),
    (r"eval\s*\(", "Dynamic evaluation"),
    (r"__import__\s*\(", "Dynamic import"),
]


class Guardrails(LoggerMixin):
    """
    Production-grade guardrails using Guardrails AI library.

    Falls back to manual validation if library not installed.

    Attributes:
        config: Guardrail configuration
        input_guard: Guard for input validation
        output_guard: Guard for output validation
        code_guard: Guard for code validation
    """

    def __init__(self, config: GuardrailConfig | None = None) -> None:
        """
        Initialize guardrails with configuration.

        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or GuardrailConfig()

        # Track which validators are available
        self._validators_status = {
            "guardrails_ai": GUARDRAILS_AVAILABLE,
            "detect_pii": DETECT_PII_AVAILABLE,
            "toxic_language": TOXIC_LANGUAGE_AVAILABLE,
            "prompt_injection": PROMPT_INJECTION_AVAILABLE,
            "valid_python": VALID_PYTHON_AVAILABLE,
        }

        self.logger.info(
            "Initializing Guardrails",
            guardrails_ai_available=GUARDRAILS_AVAILABLE,
            validators=self._validators_status
        )

        # Initialize guards if Guardrails AI is available
        self.input_guard = None
        self.output_guard = None
        self.code_guard = None

        if GUARDRAILS_AVAILABLE:
            self._setup_guards()

    def _setup_guards(self) -> None:
        """
        Set up Guardrails AI guards with validators from hub.
        """
        # Input guard - for validating user inputs
        input_validators = []

        if self.config.enable_injection_check and PROMPT_INJECTION_AVAILABLE:
            input_validators.append(
                DetectPromptInjection(on_fail="exception")
            )

        if self.config.enable_toxicity_check and TOXIC_LANGUAGE_AVAILABLE:
            input_validators.append(
                ToxicLanguage(
                    threshold=self.config.toxicity_threshold,
                    on_fail=self.config.toxicity_on_fail
                )
            )

        if input_validators:
            self.input_guard = Guard().use_many(*input_validators)
            self.logger.info(f"Input guard configured with {len(input_validators)} validators")

        # Output guard - for validating LLM outputs
        output_validators = []

        if self.config.enable_pii_filter and DETECT_PII_AVAILABLE:
            output_validators.append(
                DetectPII(on_fail=self.config.pii_on_fail)
            )

        if self.config.enable_toxicity_check and TOXIC_LANGUAGE_AVAILABLE:
            output_validators.append(
                ToxicLanguage(
                    threshold=self.config.toxicity_threshold,
                    on_fail="fix"  # Fix toxic content in output rather than reject
                )
            )

        if output_validators:
            self.output_guard = Guard().use_many(*output_validators)
            self.logger.info(f"Output guard configured with {len(output_validators)} validators")

        # Code guard - for validating generated code
        code_validators = []

        if self.config.enable_code_validation and VALID_PYTHON_AVAILABLE:
            code_validators.append(
                ValidPython(on_fail="noop")  # Don't fail, just flag
            )

        if self.config.enable_pii_filter and DETECT_PII_AVAILABLE:
            code_validators.append(
                DetectPII(on_fail="fix")
            )

        if code_validators:
            self.code_guard = Guard().use_many(*code_validators)
            self.logger.info(f"Code guard configured with {len(code_validators)} validators")

    # =========================================================================
    # INPUT VALIDATION
    # =========================================================================

    def validate_input(self, text: str, context: dict[str, Any] | None = None) -> GuardrailResult:
        """
        Validate user input before sending to LLM.

        Uses Guardrails AI if available, falls back to manual validation.

        Args:
            text: User input text
            context: Optional context (e.g., user_id, request_type)

        Returns:
            GuardrailResult with validation outcome
        """
        violations = []
        metadata = {"original_length": len(text), "using_guardrails_ai": GUARDRAILS_AVAILABLE}

        # Check 1: Length validation (always manual)
        if len(text) > self.config.max_input_length:
            return GuardrailResult(
                is_valid=False,
                action=GuardrailAction.REJECT,
                risk_level=RiskLevel.MEDIUM,
                message=f"Input too long. Maximum {self.config.max_input_length} characters allowed.",
                violations=["length_exceeded"],
                metadata=metadata
            )

        # Check 2: Use Guardrails AI if available
        if self.input_guard is not None:
            try:
                # Validate using Guardrails AI
                result = self.input_guard.validate(text)

                if result.validation_passed:
                    return GuardrailResult(
                        is_valid=True,
                        action=GuardrailAction.ALLOW,
                        risk_level=RiskLevel.LOW,
                        message="Input validated successfully via Guardrails AI",
                        metadata=metadata
                    )
                else:
                    # Extract failure info
                    for fail in result.validation_summaries:
                        violations.append(f"{fail.validator_name}: {fail.failure_reason}")

                    return GuardrailResult(
                        is_valid=False,
                        action=GuardrailAction.REJECT,
                        risk_level=RiskLevel.HIGH,
                        message="Input failed validation",
                        violations=violations,
                        metadata=metadata
                    )

            except GuardrailsValidationError as e:
                self.logger.warning(f"Guardrails validation exception: {e}")
                return GuardrailResult(
                    is_valid=False,
                    action=GuardrailAction.REJECT,
                    risk_level=RiskLevel.CRITICAL,
                    message=str(e),
                    violations=["guardrails_exception"],
                    metadata=metadata
                )

            except Exception as e:
                self.logger.error(f"Unexpected guardrails error: {e}")
                # Fall through to manual validation

        # Fallback: Manual validation
        return self._manual_validate_input(text, metadata)

    def _manual_validate_input(self, text: str, metadata: dict) -> GuardrailResult:
        """
        Manual input validation (fallback when Guardrails AI not available).
        """
        violations = []
        metadata["validation_method"] = "manual"

        # Check for prompt injection
        if self.config.enable_injection_check:
            text_lower = text.lower()
            for pattern in INJECTION_PATTERNS:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    violations.append(f"injection_pattern:{pattern[:30]}")

        # Check content policy
        if self.config.enable_content_policy:
            harmful_patterns = [
                (r"(create|write|generate)\s+(malware|virus|exploit)", "malware_request"),
                (r"(hack|attack|ddos)\s+(into|against)", "attack_request"),
            ]
            for pattern, violation_type in harmful_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(violation_type)

        if violations:
            return GuardrailResult(
                is_valid=False,
                action=GuardrailAction.REJECT,
                risk_level=RiskLevel.HIGH,
                message="Input contains potentially harmful content",
                violations=violations,
                metadata=metadata
            )

        return GuardrailResult(
            is_valid=True,
            action=GuardrailAction.ALLOW,
            risk_level=RiskLevel.LOW,
            message="Input validated successfully (manual check)",
            metadata=metadata
        )

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

        Uses Guardrails AI if available, falls back to manual validation.

        Args:
            text: LLM output text
            output_type: Type of output ("text", "code", "mixed")
            context: Optional context

        Returns:
            GuardrailResult (may include modified content)
        """
        violations = []
        modified_text = text
        metadata = {"output_type": output_type, "using_guardrails_ai": GUARDRAILS_AVAILABLE}

        # Check 1: Length
        if len(text) > self.config.max_output_length:
            modified_text = text[:self.config.max_output_length] + "\n\n[Output truncated]"
            violations.append("length_truncated")

        # Check 2: Use Guardrails AI if available
        if self.output_guard is not None:
            try:
                result = self.output_guard.validate(modified_text)

                if result.validation_passed:
                    # Check if content was modified (e.g., PII redacted)
                    if result.validated_output != modified_text:
                        modified_text = result.validated_output
                        violations.append("content_modified_by_guardrails")
                else:
                    for fail in result.validation_summaries:
                        violations.append(f"{fail.validator_name}: {fail.failure_reason}")

                metadata["guardrails_passed"] = result.validation_passed

            except Exception as e:
                self.logger.warning(f"Output validation error: {e}")
                # Fall through to manual validation

        # Fallback: Manual PII filtering
        if self.config.enable_pii_filter and not DETECT_PII_AVAILABLE:
            modified_text, pii_found = self._manual_filter_pii(modified_text)
            if pii_found:
                violations.extend(pii_found)

        action = GuardrailAction.ALLOW
        if modified_text != text:
            action = GuardrailAction.MODIFY
        elif violations:
            action = GuardrailAction.WARN

        return GuardrailResult(
            is_valid=True,
            action=action,
            risk_level=RiskLevel.LOW if not violations else RiskLevel.MEDIUM,
            message="Output processed successfully",
            modified_content=modified_text if modified_text != text else None,
            violations=violations,
            metadata=metadata
        )

    def _manual_filter_pii(self, text: str) -> tuple[str, list[str]]:
        """
        Manual PII filtering (fallback).
        """
        filtered = text
        found = []

        for pattern, pii_type, replacement in PII_PATTERNS:
            if re.search(pattern, filtered):
                filtered = re.sub(pattern, replacement, filtered)
                found.append(f"pii:{pii_type}")

        return filtered, found

    # =========================================================================
    # CODE VALIDATION
    # =========================================================================

    def validate_generated_code(self, code: str, language: str = "python") -> GuardrailResult:
        """
        Validate generated code.

        Uses Guardrails AI ValidPython if available, plus manual safety checks.

        Args:
            code: Generated code
            language: Programming language

        Returns:
            Validation result
        """
        violations = []
        metadata = {"language": language, "using_guardrails_ai": GUARDRAILS_AVAILABLE}

        # Check 1: Use Guardrails AI code guard if available
        if self.code_guard is not None and language == "python":
            try:
                result = self.code_guard.validate(code)

                if not result.validation_passed:
                    for fail in result.validation_summaries:
                        violations.append(f"{fail.validator_name}: {fail.failure_reason}")

                # Check if PII was redacted
                if result.validated_output != code:
                    code = result.validated_output
                    violations.append("pii_redacted_from_code")

            except Exception as e:
                self.logger.warning(f"Code validation error: {e}")

        # Check 2: Manual dangerous pattern check (always run)
        for pattern, description in DANGEROUS_CODE_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(description)

        risk_level = RiskLevel.LOW
        if len(violations) >= 3:
            risk_level = RiskLevel.HIGH
        elif len(violations) >= 1:
            risk_level = RiskLevel.MEDIUM

        return GuardrailResult(
            is_valid=len(violations) == 0 or risk_level == RiskLevel.LOW,
            action=GuardrailAction.WARN if violations else GuardrailAction.ALLOW,
            risk_level=risk_level,
            message="Code validation complete",
            violations=violations,
            metadata=metadata
        )

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_status(self) -> dict[str, Any]:
        """
        Get status of guardrails system.

        Returns:
            Dict with availability info for each validator
        """
        return {
            "guardrails_ai_installed": GUARDRAILS_AVAILABLE,
            "validators": self._validators_status,
            "input_guard_active": self.input_guard is not None,
            "output_guard_active": self.output_guard is not None,
            "code_guard_active": self.code_guard is not None,
            "config": {
                "enable_pii_filter": self.config.enable_pii_filter,
                "enable_toxicity_check": self.config.enable_toxicity_check,
                "enable_injection_check": self.config.enable_injection_check,
                "enable_code_validation": self.config.enable_code_validation,
            }
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

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
    """Quick validation of a prompt."""
    return get_guardrails().validate_input(text)


def validate_response(text: str, output_type: str = "text") -> GuardrailResult:
    """Quick validation of a response."""
    return get_guardrails().validate_output(text, output_type)
