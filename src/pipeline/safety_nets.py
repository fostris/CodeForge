"""Shared safety-net helpers for generated implementation and test code."""

import re

from src.config import get_logger


logger = get_logger(__name__)


def _fix_declarative_base(code: str) -> str:
    """Fix SQLAlchemy DeclarativeBase/declarative_base patterns."""
    # Fix: Base = DeclarativeBase() → class Base(DeclarativeBase): pass
    if "DeclarativeBase()" in code:
        logger.warning("Fixing DeclarativeBase() → class Base(DeclarativeBase): pass")
        code = code.replace("Base = DeclarativeBase()", "class Base(DeclarativeBase):\n    pass")
    # Fix: from sqlalchemy.ext.declarative import declarative_base (removed in SA 2.0)
    if "from sqlalchemy.ext.declarative import declarative_base" in code:
        logger.warning("Fixing deprecated declarative_base import")
        code = code.replace(
            "from sqlalchemy.ext.declarative import declarative_base",
            "from sqlalchemy.orm import DeclarativeBase"
        )
        code = code.replace("Base = declarative_base()", "class Base(DeclarativeBase):\n    pass")
    return code


def _fix_missing_pydantic_imports(code: str) -> str:
    """Fix missing BaseModel/BaseSettings/Field imports."""
    # Fix: BaseModel used but not imported
    if "BaseModel" in code and "import BaseModel" not in code and "from pydantic" not in code:
        logger.warning("Code uses BaseModel but missing import — auto-prepending")
        code = "from pydantic import BaseModel\n" + code

    # Fix: BaseSettings used but not imported
    if "BaseSettings" in code and "import BaseSettings" not in code and "from pydantic_settings" not in code:
        logger.warning("Code uses BaseSettings but missing import — auto-prepending")
        code = "from pydantic_settings import BaseSettings\n" + code

    # Fix: Field used but not imported (must come from pydantic, not pydantic_settings)
    if re.search(r'\bField\(', code) and "import Field" not in code:
        if "from pydantic import BaseModel" in code:
            # Extend existing pydantic import
            if "Field" not in code.split("from pydantic import")[1].split("\n")[0]:
                logger.warning("Code uses Field() but missing import — adding to pydantic import")
                code = code.replace("from pydantic import BaseModel",
                                    "from pydantic import BaseModel, Field")
        elif "from pydantic" not in code or "Field" not in code:
            logger.warning("Code uses Field() but missing import — auto-prepending")
            code = "from pydantic import Field\n" + code

    return code


def _fix_pydantic_validator_decorators(code: str) -> str:
    """Fix missing pydantic validator decorator imports."""
    # Fix: field_validator / model_validator used but not imported
    if "@field_validator" in code and "import field_validator" not in code:
        if "from pydantic import" in code:
            pydantic_match = re.search(r'from pydantic import (.+)', code)
            if pydantic_match and "field_validator" not in pydantic_match.group(1):
                logger.warning("Code uses @field_validator but missing import — adding")
                code = code.replace(pydantic_match.group(0),
                                    pydantic_match.group(0) + ", field_validator")
        else:
            logger.warning("Code uses @field_validator but missing import — auto-prepending")
            code = "from pydantic import field_validator\n" + code

    if "@model_validator" in code and "import model_validator" not in code:
        if "from pydantic import" in code:
            pydantic_match = re.search(r'from pydantic import (.+)', code)
            if pydantic_match and "model_validator" not in pydantic_match.group(1):
                logger.warning("Code uses @model_validator but missing import — adding")
                code = code.replace(pydantic_match.group(0),
                                    pydantic_match.group(0) + ", model_validator")
        else:
            logger.warning("Code uses @model_validator but missing import — auto-prepending")
            code = "from pydantic import model_validator\n" + code

    return code


def _fix_raise_validation_error(code: str) -> str:
    """Replace direct ValidationError() raises with ValueError() when safe."""
    # Fix: raise ValidationError("string") — pydantic v2 ValidationError has no simple constructor
    # Replace with ValueError which works everywhere
    # BUT: skip if the file defines its own ValidationError class (custom exception)
    if re.search(r'raise\s+ValidationError\s*\(', code):
        has_local_class = bool(re.search(r'class\s+ValidationError\b', code))
        if has_local_class:
            logger.debug("Code defines its own ValidationError class — skipping replacement")
        elif "from_exception_data" not in code:
            logger.warning("Code raises ValidationError() directly — replacing with ValueError()")
            code = re.sub(r'raise\s+ValidationError\(', 'raise ValueError(', code)
            # Add alias so 'from module import ValidationError' still works
            if "ValidationError = ValueError" not in code:
                # Insert alias after imports block
                lines = code.split('\n')
                insert_idx = 0
                for idx, line in enumerate(lines):
                    if line.startswith(('import ', 'from ')) or line == '':
                        insert_idx = idx + 1
                    else:
                        break
                lines.insert(insert_idx, "ValidationError = ValueError  # alias for pydantic v2 compat")
                code = '\n'.join(lines)

    return code


def _fix_field_wrong_package(code: str) -> str:
    """Move Field import from pydantic_settings to pydantic."""
    # Fix: from pydantic_settings import Field (wrong location)
    if "from pydantic_settings import" in code and "Field" in code:
        line_match = re.search(r'from pydantic_settings import (.+)', code)
        if line_match:
            imports = line_match.group(1)
            if "Field" in imports:
                logger.warning("Fixing Field import: moving from pydantic_settings to pydantic")
                # Remove Field from pydantic_settings import
                new_imports = ", ".join(
                    i.strip() for i in imports.split(",") if i.strip() != "Field"
                )
                if new_imports:
                    code = code.replace(line_match.group(0),
                                        f"from pydantic_settings import {new_imports}")
                else:
                    code = code.replace(line_match.group(0) + "\n", "")
                # Add Field to pydantic import or create new one
                if "from pydantic import" in code:
                    pydantic_match = re.search(r'from pydantic import (.+)', code)
                    if pydantic_match and "Field" not in pydantic_match.group(1):
                        code = code.replace(pydantic_match.group(0),
                                            pydantic_match.group(0) + ", Field")
                else:
                    code = "from pydantic import Field\n" + code

    return code


def _fix_missing_pytest_import(code: str) -> str:
    """Ensure pytest import is present."""
    if "import pytest" not in code:
        logger.warning("Test code missing 'import pytest' — auto-prepending")
        code = "import pytest\n" + code
    return code


def _fix_missing_jwt_import(code: str) -> str:
    """Ensure jwt import is present when jwt is used."""
    if "import jwt" not in code and "jwt." in code:
        logger.warning("Test code uses jwt but missing 'import jwt' — auto-prepending")
        code = "import jwt\n" + code
    return code


def _fix_email_error_removal(code: str) -> str:
    """Replace removed EmailError references for pydantic v2 compatibility."""
    if re.search(r'\bEmailError\b', code):
        # Only remove standalone EmailError, not compound names like DuplicateEmailError
        if re.search(r'from\s+pydantic\s+import.*\bEmailError\b', code):
            logger.warning("Test code imports EmailError (removed in pydantic v2) — removing")
            code = re.sub(r',\s*EmailError\b', '', code)
            code = re.sub(r'\bEmailError\b,\s*', '', code)
            code = re.sub(r'import\s+EmailError\b', '', code)
        # Replace standalone EmailError usage (not part of longer name)
        code = re.sub(r'(?<![A-Za-z])EmailError(?![A-Za-z])', 'Exception', code)
    return code


def _fix_explicit_init_imports(code: str) -> str:
    """Remove explicit __init__ imports."""
    if ".__init__" in code:
        logger.warning("Test code imports from __init__ explicitly — fixing")
        code = re.sub(r'\.__init__(\s)', r'\1', code)
    return code


def _fix_protocol_wrong_package(code: str) -> str:
    """Move Protocol from unittest.mock import to typing import."""
    if re.search(r'from unittest\.mock import.*Protocol', code):
        logger.warning("Test code imports Protocol from unittest.mock — fixing")
        code = re.sub(r'(from unittest\.mock import\s+)(.*),\s*Protocol\b(.*)', r'\1\2\3', code)
        code = re.sub(r'(from unittest\.mock import\s+)Protocol,\s*(.*)', r'\1\2', code)
        code = re.sub(r'(from unittest\.mock import.*),\s*\n', r'\1\n', code)
        if 'from typing import' in code:
            typing_match = re.search(r'from typing import (.+)', code)
            if typing_match and 'Protocol' not in typing_match.group(1):
                code = code.replace(typing_match.group(0), typing_match.group(0) + ', Protocol')
        else:
            code = "from typing import Protocol\n" + code
    return code


def _fix_numeric_module_imports(code: str) -> str:
    """Drop imports from numeric module names."""
    if re.search(r'from \S+\.\d', code):
        logger.warning("Test code imports from numeric filename — removing those lines")
        code = '\n'.join(
            line for line in code.split('\n')
            if not re.match(r'\s*from \S+\.\d\S* import', line)
        )
    return code


def _fix_rs256_to_hs256(code: str) -> str:
    """Replace RS256 with HS256 in tests."""
    if 'RS256' in code:
        logger.warning("Test code uses RS256 — replacing with HS256")
        code = code.replace('RS256', 'HS256')
    return code


def _fix_performance_tests(code: str) -> str:
    """Strip timing-based performance tests and asserts."""
    if re.search(r'assert\s+\w+\s*<\s*\d+', code) and 'elapsed' in code.lower():
        logger.warning("Test code has timing assertions — stripping performance test functions")
        code = re.sub(
            r'\n(    )?def test_\w*(?:perform|timing|speed|bench|_under_\d+)\w*\(.*?\n(?=(?:    )?(?:def |class |\Z))',
            '\n', code, flags=re.DOTALL,
        )
        code = re.sub(r'\n\s*assert\s+elapsed\w*\s*<\s*\d+.*', '', code)
    return code


def fix_impl_code(code: str) -> str:
    """Fix common LLM mistakes in implementation code before writing to disk."""
    if code is None:
        return None
    if code == "":
        return ""

    for fixer in (
        _fix_declarative_base,
        _fix_missing_pydantic_imports,
        _fix_pydantic_validator_decorators,
        _fix_raise_validation_error,
        _fix_field_wrong_package,
    ):
        code = fixer(code)

    return code


def fix_test_code(code: str) -> str:
    """Apply all test safety nets to generated test code."""
    if not code:
        return code

    for fixer in (
        _fix_missing_pytest_import,
        _fix_missing_jwt_import,
        _fix_email_error_removal,
        _fix_explicit_init_imports,
        _fix_protocol_wrong_package,
        _fix_numeric_module_imports,
        _fix_rs256_to_hs256,
        _fix_raise_validation_error,
        _fix_missing_pydantic_imports,
        _fix_field_wrong_package,
        _fix_performance_tests,
    ):
        code = fixer(code)

    return code
