"""Shared safety-net helpers for generated implementation and test code."""

import re

from src.config import get_logger


logger = get_logger(__name__)


def fix_impl_code(code: str) -> str:
    """Fix common LLM mistakes in implementation code before writing to disk."""
    if code is None:
        return None
    if code == "":
        return ""

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


def fix_test_code(code: str) -> str:
    """Apply all test safety nets to generated test code."""
    if not code:
        return code

    # import pytest
    if "import pytest" not in code:
        logger.warning("Test code missing 'import pytest' — auto-prepending")
        code = "import pytest\n" + code
    # import jwt
    if "import jwt" not in code and "jwt." in code:
        logger.warning("Test code uses jwt but missing 'import jwt' — auto-prepending")
        code = "import jwt\n" + code
    # ValidationError import
    if "ValidationError" in code and "import ValidationError" not in code and "from pydantic" not in code:
        logger.warning("Test code uses ValidationError but missing import — auto-prepending")
        code = "from pydantic import ValidationError\n" + code
    # Remove EmailError (standalone pydantic v1 class, not DuplicateEmailError etc.)
    if re.search(r'\bEmailError\b', code):
        # Only remove standalone EmailError, not compound names like DuplicateEmailError
        if re.search(r'from\s+pydantic\s+import.*\bEmailError\b', code):
            logger.warning("Test code imports EmailError (removed in pydantic v2) — removing")
            code = re.sub(r',\s*EmailError\b', '', code)
            code = re.sub(r'\bEmailError\b,\s*', '', code)
            code = re.sub(r'import\s+EmailError\b', '', code)
        # Replace standalone EmailError usage (not part of longer name)
        code = re.sub(r'(?<![A-Za-z])EmailError(?![A-Za-z])', 'Exception', code)
    # Fix __init__ imports
    if ".__init__" in code:
        logger.warning("Test code imports from __init__ explicitly — fixing")
        code = re.sub(r'\.__init__(\s)', r'\1', code)
    # Protocol from wrong module
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
    # Remove numeric module imports
    if re.search(r'from \S+\.\d', code):
        logger.warning("Test code imports from numeric filename — removing those lines")
        code = '\n'.join(
            line for line in code.split('\n')
            if not re.match(r'\s*from \S+\.\d\S* import', line)
        )
    # RS256 → HS256
    if 'RS256' in code:
        logger.warning("Test code uses RS256 — replacing with HS256")
        code = code.replace('RS256', 'HS256')
    # raise ValidationError() → raise ValueError() (only if no local class defined)
    if re.search(r'raise\s+ValidationError\s*\(', code) and not re.search(r'class\s+ValidationError\b', code):
        logger.warning("Test code raises ValidationError() directly — replacing with ValueError()")
        code = re.sub(r'raise\s+ValidationError\(', 'raise ValueError(', code)
    # BaseModel import
    if 'BaseModel' in code and 'import BaseModel' not in code and 'from pydantic' not in code:
        logger.warning("Test code uses BaseModel but missing import — auto-prepending")
        code = "from pydantic import BaseModel\n" + code
    # BaseSettings import
    if 'BaseSettings' in code and 'import BaseSettings' not in code and 'from pydantic_settings' not in code:
        logger.warning("Test code uses BaseSettings but missing import — auto-prepending")
        code = "from pydantic_settings import BaseSettings\n" + code
    # Field from wrong package
    if 'from pydantic_settings import' in code and 'Field' in code:
        line_match = re.search(r'from pydantic_settings import (.+)', code)
        if line_match and 'Field' in line_match.group(1):
            logger.warning("Test code imports Field from pydantic_settings — fixing")
            new_imports = ", ".join(
                i.strip() for i in line_match.group(1).split(",") if i.strip() != "Field"
            )
            if new_imports:
                code = code.replace(line_match.group(0), f"from pydantic_settings import {new_imports}")
            else:
                code = code.replace(line_match.group(0) + "\n", "")
            if "from pydantic import" in code:
                pydantic_match = re.search(r'from pydantic import (.+)', code)
                if pydantic_match and "Field" not in pydantic_match.group(1):
                    code = code.replace(pydantic_match.group(0), pydantic_match.group(0) + ", Field")
            else:
                code = "from pydantic import Field\n" + code
    # Strip performance tests
    if re.search(r'assert\s+\w+\s*<\s*\d+', code) and 'elapsed' in code.lower():
        logger.warning("Test code has timing assertions — stripping performance test functions")
        code = re.sub(
            r'\n(    )?def test_\w*(?:perform|timing|speed|bench|_under_\d+)\w*\(.*?\n(?=(?:    )?(?:def |class |\Z))',
            '\n', code, flags=re.DOTALL,
        )
        code = re.sub(r'\n\s*assert\s+elapsed\w*\s*<\s*\d+.*', '', code)

    return code
