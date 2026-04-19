"""Tests for safety net fixes."""

import pytest

from src.pipeline.safety_nets import (
    fix_impl_code,
    fix_test_code,
    _fix_declarative_base,
    _fix_missing_pydantic_imports,
    _fix_pydantic_validator_decorators,
    _fix_field_wrong_package,
    _fix_raise_validation_error,
    _fix_missing_pytest_import,
    _fix_missing_jwt_import,
    _fix_email_error_removal,
    _fix_explicit_init_imports,
    _fix_protocol_wrong_package,
    _fix_numeric_module_imports,
    _fix_rs256_to_hs256,
    _fix_performance_tests,
)


# ---------------------------------------------------------------------------
# Implementation fixes
# ---------------------------------------------------------------------------

class TestDeclarativeBase:
    def test_replaces_function_call_with_subclass(self):
        code = "Base = DeclarativeBase()"
        assert "class Base(DeclarativeBase):" in _fix_declarative_base(code)

    def test_replaces_deprecated_helper(self):
        code = (
            "from sqlalchemy.ext.declarative import declarative_base\n"
            "Base = declarative_base()"
        )
        result = _fix_declarative_base(code)
        assert "from sqlalchemy.orm import DeclarativeBase" in result
        assert "class Base(DeclarativeBase):" in result

    def test_leaves_correct_code_alone(self):
        code = "class Base(DeclarativeBase):\n    pass"
        assert _fix_declarative_base(code) == code


class TestMissingPydanticImports:
    def test_adds_basemodel(self):
        code = "class User(BaseModel):\n    id: int"
        result = _fix_missing_pydantic_imports(code)
        assert "from pydantic import BaseModel" in result

    def test_adds_basesettings(self):
        code = "class Settings(BaseSettings):\n    db: str"
        result = _fix_missing_pydantic_imports(code)
        assert "from pydantic_settings import BaseSettings" in result

    def test_adds_field_to_existing_import(self):
        code = "from pydantic import BaseModel\n\nclass X(BaseModel):\n    y: int = Field(default=1)"
        result = _fix_missing_pydantic_imports(code)
        assert "from pydantic import BaseModel, Field" in result

    def test_leaves_code_with_imports_alone(self):
        code = "from pydantic import BaseModel\nclass X(BaseModel): pass"
        assert _fix_missing_pydantic_imports(code) == code


class TestPydanticValidatorDecorators:
    def test_adds_field_validator_to_existing_import(self):
        code = "from pydantic import BaseModel\n\n@field_validator('x')\ndef v(cls, v): return v"
        result = _fix_pydantic_validator_decorators(code)
        assert "field_validator" in result.split("\n")[0]

    def test_prepends_field_validator_when_no_pydantic_import(self):
        code = "@field_validator('x')\ndef v(cls, v): return v"
        result = _fix_pydantic_validator_decorators(code)
        assert result.startswith("from pydantic import field_validator")

    def test_adds_model_validator(self):
        code = "from pydantic import BaseModel\n\n@model_validator(mode='after')\ndef v(self): return self"
        result = _fix_pydantic_validator_decorators(code)
        assert "model_validator" in result.split("\n")[0]


class TestFieldWrongPackage:
    def test_moves_field_from_pydantic_settings_to_pydantic(self):
        code = "from pydantic_settings import BaseSettings, Field\n\nclass X(BaseSettings):\n    y: int = Field(default=1)"
        result = _fix_field_wrong_package(code)
        assert "from pydantic_settings import BaseSettings" in result
        assert "Field" not in result.split("from pydantic_settings")[1].split("\n")[0]
        assert "Field" in result  # moved elsewhere

    def test_leaves_correct_imports_alone(self):
        code = "from pydantic import Field\nfrom pydantic_settings import BaseSettings"
        assert _fix_field_wrong_package(code) == code


class TestRaiseValidationError:
    def test_replaces_raise_validation_error(self):
        code = "from pydantic import ValidationError\n\ndef f():\n    raise ValidationError('bad')"
        result = _fix_raise_validation_error(code)
        assert "raise ValueError('bad')" in result
        assert "ValidationError = ValueError" in result  # alias added

    def test_leaves_local_class_alone(self):
        code = "class ValidationError(Exception):\n    pass\n\ndef f():\n    raise ValidationError('x')"
        assert _fix_raise_validation_error(code) == code

    def test_leaves_from_exception_data_alone(self):
        code = "ValidationError.from_exception_data('msg', [])"
        assert _fix_raise_validation_error(code) == code


# ---------------------------------------------------------------------------
# Test-code fixes
# ---------------------------------------------------------------------------

class TestMissingPytestImport:
    def test_prepends_when_missing(self):
        code = "def test_foo():\n    assert True"
        result = _fix_missing_pytest_import(code)
        assert result.startswith("import pytest")

    def test_leaves_alone_when_present(self):
        code = "import pytest\n\ndef test_foo(): pass"
        assert _fix_missing_pytest_import(code) == code


class TestMissingJwtImport:
    def test_adds_when_used(self):
        code = "def test_token():\n    payload = jwt.decode(t, 'secret')"
        result = _fix_missing_jwt_import(code)
        assert result.startswith("import jwt")

    def test_skips_when_jwt_not_used(self):
        code = "def test_other(): pass"
        assert _fix_missing_jwt_import(code) == code


class TestEmailErrorRemoval:
    def test_removes_standalone_email_error_import(self):
        code = "from pydantic import EmailError\n\nraise EmailError('bad')"
        result = _fix_email_error_removal(code)
        assert "EmailError" not in result.split("\n")[0]
        assert "raise Exception" in result

    def test_preserves_compound_names(self):
        code = "from src.auth import DuplicateEmailError\nraise DuplicateEmailError('x')"
        result = _fix_email_error_removal(code)
        assert "DuplicateEmailError" in result

    def test_removes_from_combined_import(self):
        code = "from pydantic import BaseModel, EmailError, Field"
        result = _fix_email_error_removal(code)
        assert "EmailError" not in result


class TestExplicitInitImports:
    def test_removes_explicit_init(self):
        code = "from src.auth.models.__init__ import Base"
        result = _fix_explicit_init_imports(code)
        assert ".__init__" not in result
        assert "from src.auth.models import Base" in result


class TestProtocolWrongPackage:
    def test_moves_protocol_to_typing(self):
        code = "from unittest.mock import Mock, Protocol"
        result = _fix_protocol_wrong_package(code)
        assert "from typing import Protocol" in result
        assert "Protocol" not in result.split("from unittest.mock")[1].split("\n")[0]


class TestNumericModuleImports:
    def test_drops_numeric_module_import(self):
        code = "from migrations.001_create_users import upgrade\nfrom src.auth import User"
        result = _fix_numeric_module_imports(code)
        assert "001_create_users" not in result
        assert "src.auth" in result


class TestRs256ToHs256:
    def test_replaces_all_occurrences(self):
        code = "algorithm='RS256'\n# comment about RS256"
        result = _fix_rs256_to_hs256(code)
        assert "RS256" not in result
        assert result.count("HS256") == 2


class TestPerformanceTests:
    def test_strips_timing_test(self):
        code = (
            "import pytest\n"
            "import time\n\n"
            "def test_normal():\n"
            "    assert 1 == 1\n\n"
            "def test_hash_performance_under_50ms():\n"
            "    start = time.time()\n"
            "    hash_password('x')\n"
            "    elapsed = time.time() - start\n"
            "    assert elapsed < 0.05\n"
        )
        result = _fix_performance_tests(code)
        assert "test_normal" in result
        assert "test_hash_performance_under_50ms" not in result

    def test_leaves_non_timing_asserts_alone(self):
        code = "def test_x():\n    assert len(result) < 100\n    assert result.status == 200"
        # no 'elapsed' keyword, so function shouldn't be stripped
        result = _fix_performance_tests(code)
        assert "test_x" in result


# ---------------------------------------------------------------------------
# Top-level entry points
# ---------------------------------------------------------------------------

class TestFixImplCode:
    def test_empty_input_returns_empty(self):
        assert fix_impl_code("") == ""
        assert fix_impl_code(None) is None

    def test_applies_multiple_fixes(self):
        code = (
            "Base = DeclarativeBase()\n"
            "class User(BaseModel):\n"
            "    id: int"
        )
        result = fix_impl_code(code)
        assert "class Base(DeclarativeBase):" in result
        assert "from pydantic import BaseModel" in result

    def test_idempotent(self):
        code = (
            "Base = DeclarativeBase()\n"
            "class User(BaseModel):\n"
            "    id: int"
        )
        once = fix_impl_code(code)
        twice = fix_impl_code(once)
        assert once == twice


class TestFixTestCode:
    def test_empty_input(self):
        assert fix_test_code("") == ""

    def test_combines_test_and_impl_fixes(self):
        code = (
            "from pydantic_settings import Field\n"
            "def test_foo():\n"
            "    assert True"
        )
        result = fix_test_code(code)
        # pytest import added (may not be first line — other fixes can prepend)
        assert "import pytest" in result
        # Field moved from pydantic_settings to pydantic
        assert "from pydantic import Field" in result
        assert "from pydantic_settings import Field" not in result

    def test_idempotent(self):
        code = (
            "from unittest.mock import Mock, Protocol\n"
            "def test_foo():\n"
            "    assert jwt.decode(x)\n"
        )
        once = fix_test_code(code)
        twice = fix_test_code(once)
        assert once == twice
