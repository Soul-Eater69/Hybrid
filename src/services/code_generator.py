"""
Code Generation Service
=======================

Generates code using LangChain and LLM, informed by:
- Vector DB (similar code examples)
- Knowledge Graph (code structure and relationships)

WHAT THIS SERVICE DOES:
    Takes a natural language prompt and generates code that:
    1. Follows the patterns in the existing codebase
    2. Is consistent with the project's style
    3. Integrates properly with existing code

HOW IT WORKS:
    1. User provides a prompt describing what code to generate
    2. Search Vector DB for similar code examples
    3. Query Knowledge Graph for related entities
    4. Build context from examples and relationships
    5. Use LangChain to construct the LLM prompt
    6. Generate code with the LLM
    7. Return code with explanation

RAG (RETRIEVAL AUGMENTED GENERATION):
    We use RAG to improve code generation quality:

    ┌─────────────────────────────────────────────────────────────┐
    │                    USER PROMPT                               │
    │    "Create a function to validate phone numbers"            │
    └─────────────────────────────────────────────────────────────┘
                               ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                   RETRIEVAL STEP                             │
    │  Vector DB: Find similar validation functions               │
    │  Neo4j: Find related validators, utilities                  │
    └─────────────────────────────────────────────────────────────┘
                               ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                 CONTEXT BUILDING                             │
    │  - Similar code: validate_email(), validate_username()      │
    │  - Project style: Type hints, docstrings, error handling    │
    │  - Related imports: re, phonenumbers library                │
    └─────────────────────────────────────────────────────────────┘
                               ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                   LLM GENERATION                             │
    │  Prompt = User Request + Retrieved Context + Instructions   │
    │  → GPT-4 → Generated Code                                   │
    └─────────────────────────────────────────────────────────────┘
                               ↓
    ┌─────────────────────────────────────────────────────────────┐
    │                      OUTPUT                                  │
    │  def validate_phone(phone: str) -> bool:                    │
    │      '''Validate phone number format.'''                    │
    │      ...                                                     │
    └─────────────────────────────────────────────────────────────┘

LANGCHAIN COMPONENTS USED:
    - ChatOpenAI: LLM for generation
    - PromptTemplate: Structured prompts
    - LLMChain: Chain for generation

USAGE:
    from src.services.code_generator import CodeGenerator

    generator = CodeGenerator(neo4j, vector_svc)

    result = await generator.generate(
        repository_id="repo-123",
        prompt="Create a function to validate phone numbers",
        context_entities=["validate_email"],  # Use as example
        include_tests=True
    )

    print(result.code)
    print(result.explanation)
"""

import asyncio
from typing import Any
from uuid import uuid4

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.core.exceptions import LLMError
from src.core.logging import LoggerMixin
from src.services.neo4j_service import Neo4jService
from src.services.vector_service import VectorService


# System prompt for code generation
CODE_GENERATION_SYSTEM_PROMPT = """You are an expert software engineer helping to generate code.
You will be given:
1. A description of what code to write
2. Examples of similar code from the same codebase
3. Information about related code entities

Your task is to generate code that:
- Follows the patterns and style of the provided examples
- Is consistent with the project's conventions
- Is well-documented with docstrings
- Uses type hints where appropriate
- Handles errors appropriately
- Is production-ready

Respond with the generated code, followed by a brief explanation of what the code does and any important implementation decisions."""

# Prompt template for code generation
CODE_GENERATION_TEMPLATE = """
## Task Description
{prompt}

## Similar Code Examples (for reference)
{similar_code}

## Related Entities in the Codebase
{related_entities}

## Target File (if specified)
{target_file}

## Style Guide
{style_guide}

## Instructions
Generate the code based on the task description above. Follow the patterns shown in the similar code examples.
Make sure your code integrates well with the related entities shown.

Respond in the following format:
```python
# Your generated code here
```

## Explanation
Explain what the code does and any important decisions made.
"""

# Test generation template
TEST_GENERATION_TEMPLATE = """
## Code to Test
```python
{code}
```

## Existing Test Patterns (for reference)
{test_examples}

## Instructions
Generate comprehensive unit tests for the code above using pytest.
Include:
- Happy path tests
- Edge cases
- Error handling tests

Follow the test patterns shown in the examples.

```python
# Your test code here
```
"""


class CodeGenerator(LoggerMixin):
    """
    Service for AI-powered code generation.

    Uses LangChain with OpenAI to generate code based on
    context from the knowledge graph and vector database.

    Attributes:
        neo4j: Neo4j service for graph queries
        vector: Vector service for similar code search
        llm: LangChain ChatOpenAI instance
    """

    def __init__(
        self,
        neo4j: Neo4jService,
        vector: VectorService
    ) -> None:
        """
        Initialize the code generator.

        Args:
            neo4j: Neo4j service instance
            vector: Vector service instance
        """
        self.neo4j = neo4j
        self.vector = vector

        # Initialize LangChain LLM
        self._llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.2,  # Lower temperature for more consistent code
            api_key=settings.openai_api_key,
            max_tokens=4000
        )

    async def generate(
        self,
        repository_id: str,
        prompt: str,
        context_entities: list[str] | None = None,
        target_file: str | None = None,
        similar_code_count: int = 5,
        include_tests: bool = False,
        style_guide: str | None = None
    ) -> dict[str, Any]:
        """
        Generate code based on a natural language prompt.

        Uses RAG (Retrieval Augmented Generation) to provide
        relevant context from the codebase.

        Args:
            repository_id: UUID of the repository
            prompt: Natural language description of code to generate
            context_entities: Names of entities to use as context
            target_file: Target file path for the generated code
            similar_code_count: Number of similar examples to retrieve
            include_tests: Whether to also generate tests
            style_guide: Specific style guidelines to follow

        Returns:
            Dict with generated code, explanation, and metadata

        Example:
            result = await generator.generate(
                repository_id="repo-123",
                prompt="Create a function to calculate order total with tax",
                context_entities=["calculate_subtotal"],
                include_tests=True
            )
        """
        self.logger.info(
            "Starting code generation",
            repository_id=repository_id,
            prompt=prompt[:100]
        )

        try:
            # Step 1: Retrieve similar code from Vector DB
            similar_code = await self._retrieve_similar_code(
                prompt,
                repository_id,
                similar_code_count
            )

            # Step 2: Get related entities from Knowledge Graph
            related_entities = await self._get_related_entities(
                repository_id,
                context_entities
            )

            # Step 3: Build the generation prompt
            generation_prompt = self._build_prompt(
                prompt=prompt,
                similar_code=similar_code,
                related_entities=related_entities,
                target_file=target_file,
                style_guide=style_guide
            )

            # Step 4: Generate code with LLM
            generated = await self._call_llm(generation_prompt)

            # Step 5: Parse the response
            code, explanation = self._parse_response(generated)

            # Step 6: Generate tests if requested
            tests = None
            if include_tests:
                tests = await self._generate_tests(code, repository_id)

            # Build result
            result = {
                "id": str(uuid4()),
                "prompt": prompt,
                "generated": {
                    "code": code,
                    "explanation": explanation,
                    "similar_examples": [
                        {
                            "entity_id": s["entity_id"],
                            "name": s["metadata"].get("name", ""),
                            "score": s["score"]
                        }
                        for s in similar_code
                    ],
                    "tests": tests,
                    "confidence_score": self._calculate_confidence(
                        similar_code,
                        code
                    ),
                    "tokens_used": len(generation_prompt.split()) * 2  # Rough estimate
                },
                "metadata": {
                    "repository_id": repository_id,
                    "target_file": target_file,
                    "context_entities": context_entities,
                    "model": settings.openai_model
                }
            }

            self.logger.info(
                "Code generation complete",
                code_lines=len(code.splitlines())
            )

            return result

        except Exception as e:
            self.logger.error("Code generation failed", error=str(e))
            raise LLMError(f"Generation failed: {e}", model=settings.openai_model)

    async def _retrieve_similar_code(
        self,
        prompt: str,
        repository_id: str,
        limit: int
    ) -> list[dict[str, Any]]:
        """
        Retrieve similar code from the vector database.

        Args:
            prompt: User's prompt
            repository_id: Repository ID
            limit: Maximum results

        Returns:
            List of similar code results
        """
        try:
            results = await self.vector.search(
                query=prompt,
                repository_id=repository_id,
                limit=limit,
                entity_types=["function", "class"]  # Most relevant for generation
            )
            return results
        except Exception as e:
            self.logger.warning(
                "Similar code retrieval failed",
                error=str(e)
            )
            return []

    async def _get_related_entities(
        self,
        repository_id: str,
        context_entities: list[str] | None
    ) -> list[dict[str, Any]]:
        """
        Get related entities from the knowledge graph.

        Args:
            repository_id: Repository ID
            context_entities: Specific entity names to include

        Returns:
            List of related entity information
        """
        related = []

        if not context_entities:
            return related

        for entity_name in context_entities:
            entity = await self.neo4j.get_entity_by_name(
                entity_name,
                repository_id
            )
            if entity:
                related.append(entity)

                # Also get entities this one depends on
                deps = await self.neo4j.get_dependencies(
                    entity["id"],
                    max_depth=1
                )
                for dep in deps[:3]:  # Limit to avoid overwhelming context
                    related.append(dep["entity"])

        return related

    def _build_prompt(
        self,
        prompt: str,
        similar_code: list[dict[str, Any]],
        related_entities: list[dict[str, Any]],
        target_file: str | None,
        style_guide: str | None
    ) -> str:
        """
        Build the full prompt for the LLM.

        Args:
            prompt: User's prompt
            similar_code: Similar code examples
            related_entities: Related entities
            target_file: Target file path
            style_guide: Style guidelines

        Returns:
            Full prompt string
        """
        # Format similar code
        similar_code_str = ""
        for i, code in enumerate(similar_code, 1):
            name = code.get("metadata", {}).get("name", f"Example {i}")
            document = code.get("document", "")
            similar_code_str += f"\n### Example {i}: {name}\n{document}\n"

        if not similar_code_str:
            similar_code_str = "(No similar code found in the codebase)"

        # Format related entities
        related_str = ""
        for entity in related_entities:
            name = entity.get("name", "Unknown")
            entity_type = entity.get("entity_type", "unknown")
            file_path = entity.get("file_path", "unknown")
            source = entity.get("source_code", "")[:500]  # Limit size
            related_str += f"\n### {entity_type}: {name}\nFile: {file_path}\n```python\n{source}\n```\n"

        if not related_str:
            related_str = "(No related entities specified)"

        # Format template
        template = PromptTemplate(
            input_variables=[
                "prompt",
                "similar_code",
                "related_entities",
                "target_file",
                "style_guide"
            ],
            template=CODE_GENERATION_TEMPLATE
        )

        return template.format(
            prompt=prompt,
            similar_code=similar_code_str,
            related_entities=related_str,
            target_file=target_file or "(Not specified - use appropriate conventions)",
            style_guide=style_guide or "Follow PEP 8, use type hints, include docstrings"
        )

    async def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM with the prompt.

        Args:
            prompt: Full generation prompt

        Returns:
            LLM response text
        """
        messages = [
            SystemMessage(content=CODE_GENERATION_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        # Use asyncio.to_thread for the synchronous LangChain call
        response = await asyncio.to_thread(
            self._llm.invoke,
            messages
        )

        return response.content

    def _parse_response(self, response: str) -> tuple[str, str]:
        """
        Parse the LLM response to extract code and explanation.

        Args:
            response: Raw LLM response

        Returns:
            Tuple of (code, explanation)
        """
        code = ""
        explanation = ""

        # Extract code blocks
        import re
        code_blocks = re.findall(
            r'```(?:python)?\n(.*?)```',
            response,
            re.DOTALL
        )

        if code_blocks:
            code = code_blocks[0].strip()

        # Extract explanation (text after code block)
        if "## Explanation" in response:
            explanation = response.split("## Explanation")[-1].strip()
        elif code_blocks:
            # Get text after the last code block
            parts = response.split("```")
            if len(parts) > 2:
                explanation = parts[-1].strip()

        if not explanation:
            explanation = "Code generated based on provided context and examples."

        return code, explanation

    async def _generate_tests(
        self,
        code: str,
        repository_id: str
    ) -> str:
        """
        Generate tests for the generated code.

        Args:
            code: Generated code to test
            repository_id: Repository ID

        Returns:
            Generated test code
        """
        self.logger.info("Generating tests for code")

        # Find existing test examples
        test_examples = await self.vector.search(
            query="test function unittest pytest",
            repository_id=repository_id,
            limit=3,
            entity_types=["function"]
        )

        test_examples_str = ""
        for ex in test_examples:
            doc = ex.get("document", "")
            if "test" in doc.lower():
                test_examples_str += f"\n{doc}\n"

        if not test_examples_str:
            test_examples_str = "(No existing test examples found)"

        prompt = TEST_GENERATION_TEMPLATE.format(
            code=code,
            test_examples=test_examples_str
        )

        response = await self._call_llm(prompt)

        # Extract test code
        import re
        code_blocks = re.findall(
            r'```(?:python)?\n(.*?)```',
            response,
            re.DOTALL
        )

        return code_blocks[0].strip() if code_blocks else ""

    def _calculate_confidence(
        self,
        similar_code: list[dict[str, Any]],
        generated_code: str
    ) -> float:
        """
        Calculate a confidence score for the generated code.

        Based on:
        - Quality of similar examples found
        - Length and completeness of generated code

        Args:
            similar_code: Similar code results
            generated_code: Generated code

        Returns:
            Confidence score (0-1)
        """
        score = 0.5  # Base score

        # Boost for good similar examples
        if similar_code:
            avg_similarity = sum(s.get("score", 0) for s in similar_code) / len(similar_code)
            score += avg_similarity * 0.3

        # Boost for substantial generated code
        lines = generated_code.strip().split("\n")
        if len(lines) >= 5:
            score += 0.1
        if len(lines) >= 10:
            score += 0.05

        # Check for docstring
        if '"""' in generated_code or "'''" in generated_code:
            score += 0.05

        return min(score, 1.0)

    async def suggest_improvements(
        self,
        code: str,
        repository_id: str
    ) -> dict[str, Any]:
        """
        Suggest improvements for existing code.

        Args:
            code: Code to improve
            repository_id: Repository ID

        Returns:
            Dict with suggestions
        """
        prompt = f"""
Analyze the following code and suggest improvements:

```python
{code}
```

Consider:
1. Code quality and readability
2. Error handling
3. Performance
4. Best practices

Provide specific suggestions with examples.
"""

        response = await self._call_llm(prompt)

        return {
            "original_code": code,
            "suggestions": response
        }
