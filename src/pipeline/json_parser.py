"""
Robust JSON parser for LLM responses.
Drop this into src/pipeline/ and use parse_llm_json() in graph.py
instead of the current parsing logic.
"""

from __future__ import annotations

import json
import re
import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)


def parse_llm_json(response: str) -> Optional[Union[dict, list]]:
    """
    Robustly extract and parse JSON from an LLM response.
    
    Handles common LLM issues:
    1. Text before/after JSON (explanations, markdown fences)
    2. Trailing commas (e.g. [1, 2, 3,])
    3. Single-line // comments
    4. Truncated JSON (attempts bracket balancing)
    """
    
    # Step 1: Try direct parse (best case)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Step 2: Strip markdown code fences
    cleaned = re.sub(r'```json\s*', '', response)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass
    
    # Step 3: Extract the outermost JSON object/array via bracket matching
    json_str = _extract_json_by_brackets(response)
    if json_str:
        # Step 3a: Try as-is
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Step 3b: Clean trailing commas and comments, then retry
        json_str = _clean_json(json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Parse failed after cleaning: {e}")
            
            # Step 3c: Try to fix truncated JSON by closing brackets
            fixed = _fix_truncated(json_str)
            if fixed:
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError as e2:
                    logger.error(f"Parse failed even after truncation fix: {e2}")
    
    logger.error("All JSON extraction attempts failed")
    return None


def _extract_json_by_brackets(text: str) -> Optional[str]:
    """
    Find the first top-level JSON object or array by matching brackets.
    This is far more reliable than regex for nested JSON.
    """
    start = None
    open_char = None
    close_char = None
    
    for i, ch in enumerate(text):
        if ch == '{' and start is None:
            start = i
            open_char = '{'
            close_char = '}'
            break
        elif ch == '[' and start is None:
            start = i
            open_char = '['
            close_char = ']'
            break
    
    if start is None:
        return None
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start, len(text)):
        ch = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if ch == '\\' and in_string:
            escape_next = True
            continue
        
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    
    # Brackets never closed — return what we have (truncated)
    logger.warning(f"JSON brackets not balanced (depth={depth}), returning partial")
    return text[start:]


def _clean_json(json_str: str) -> str:
    """Remove trailing commas and single-line comments."""
    # Remove // comments (not inside strings — simplified approach)
    lines = json_str.split('\n')
    cleaned_lines = []
    for line in lines:
        # Simple heuristic: remove // comments that aren't inside quotes
        # This won't handle all edge cases but covers 95% of LLM output
        in_str = False
        result = []
        i = 0
        while i < len(line):
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                in_str = not in_str
            if not in_str and line[i:i+2] == '//':
                break
            result.append(line[i])
            i += 1
        cleaned_lines.append(''.join(result))
    
    json_str = '\n'.join(cleaned_lines)
    
    # Remove trailing commas: ,] or ,}
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    return json_str


def _fix_truncated(json_str: str) -> Optional[str]:
    """
    Attempt to fix truncated JSON (e.g. from max_tokens cutoff).
    
    Strategy: find the last position where a complete JSON value ended,
    cut there, then close remaining brackets in correct nesting order.
    """
    in_string = False
    escape_next = False
    bracket_stack = []  # track nesting order: '{' or '['
    last_complete_object_end = 0
    
    for i, ch in enumerate(json_str):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        
        if ch in ('{', '['):
            bracket_stack.append(ch)
        elif ch == '}':
            if bracket_stack and bracket_stack[-1] == '{':
                bracket_stack.pop()
                last_complete_object_end = i + 1
        elif ch == ']':
            if bracket_stack and bracket_stack[-1] == '[':
                bracket_stack.pop()
                last_complete_object_end = i + 1
    
    if not bracket_stack and not in_string:
        return None  # Already balanced, issue is elsewhere
    
    # If truncated mid-string or mid-value, cut back to last complete object
    if in_string or bracket_stack:
        if last_complete_object_end > 0:
            result = json_str[:last_complete_object_end]
        else:
            # No complete object found — can't recover
            return None
        
        # Remove any trailing comma after our cut point
        result = result.rstrip().rstrip(',')
        
        # Rebuild the bracket stack for the truncated result
        bracket_stack = []
        in_string = False
        escape_next = False
        for ch in result:
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ('{', '['):
                bracket_stack.append(ch)
            elif ch == '}' and bracket_stack and bracket_stack[-1] == '{':
                bracket_stack.pop()
            elif ch == ']' and bracket_stack and bracket_stack[-1] == '[':
                bracket_stack.pop()
    else:
        result = json_str
    
    # Close remaining brackets in correct reverse nesting order
    while bracket_stack:
        opener = bracket_stack.pop()
        result += '}' if opener == '{' else ']'
    
    return result


# --- Usage example for graph.py ---
#
# BEFORE (current code, fragile):
#   response_text = await cloud_client.generate(prompt)
#   data = json.loads(response_text)  # BOOM
#
# AFTER (robust):
#   from src.pipeline.json_parser import parse_llm_json
#   
#   response_text = await cloud_client.generate(prompt)
#   data = parse_llm_json(response_text)
#   if data is None:
#       logger.error("Could not parse decomposition response")
#       # Retry with explicit instruction or escalate
#   else:
#       tasks = data.get("tasks", [])
