from __future__ import annotations

import json
import re
from typing import Any, Optional

from logging import getLogger

logger = getLogger(__name__)

# OpenRouter (Claude Sonnet etc.) – key and model from config (env)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_llm(**kwargs: Any):
    """Build ChatOpenAI client for OpenRouter using OPENROUTER_API_KEY and OPENROUTER_MODEL from config."""
    from config import settings
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.OPENROUTER_MODEL,
        **kwargs,
    )

def extract_text_from_content(content) -> str:
    """
    Extract text from LLM response content which can be:
    - A string
    - A list of strings or dicts like {'type': 'text', 'text': '...'}
    - A dict like {'type': 'text', 'text': '...'}
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                # Only extract from explicit text content blocks; ignore metadata blobs
                if item.get("type") == "text":
                    text = item.get("text", "")
                    if text:
                        text_parts.append(text)
            # Ignore non-text items entirely to avoid polluting the text stream
        return "".join(text_parts)
    elif isinstance(content, dict):
        # Single dict content block (ignore non-text dicts)
        if content.get("type") == "text":
            return content.get("text", "") or ""
        return ""
    else:
        return str(content)


def extract_json_from_response(text: str) -> Optional[dict]:
    """
    Best-effort: extract the first {...} JSON object from an LLM response.
    Handles incomplete/truncated JSON by attempting to close it.
    """
    if not text:
        return None
    s = text.strip()
    
    # Try parsing the entire string as JSON first
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError as e:
        # If JSON is incomplete, try to fix it
        if e.pos >= len(s) - 100:  # Error near the end suggests truncation
            # Try to close incomplete JSON
            try:
                # Count unclosed braces/brackets
                open_braces = s.count("{") - s.count("}")
                open_brackets = s.count("[") - s.count("]")
                
                # Try to close the JSON
                fixed = s
                if open_braces > 0:
                    fixed += "\n" + "}" * open_braces
                if open_brackets > 0:
                    fixed += "\n" + "]" * open_brackets
                
                obj = json.loads(fixed)
                return obj if isinstance(obj, dict) else None
            except Exception:
                pass
    except Exception:
        pass

    # Try fenced ```json ... ``` or ``` ... ```
    # First, extract the entire content of code blocks, then find JSON within
    code_block_patterns = [
        r"```(?:json)?\s*([\s\S]*?)\s*```",  # Complete code block with closing ```
        r"```(?:json)?\s*([\s\S]+)$",  # Code block without closing ``` (incomplete)
    ]
    
    for pattern in code_block_patterns:
        m = re.search(pattern, s, flags=re.IGNORECASE | re.DOTALL)
        if m:
            code_content = m.group(1).strip()
            
            # If code content starts with {, try parsing the whole thing as JSON
            if code_content.startswith("{"):
                try:
                    obj = json.loads(code_content)
                    return obj if isinstance(obj, dict) else None
                except json.JSONDecodeError:
                    # Try to fix incomplete JSON
                    try:
                        open_braces = code_content.count("{") - code_content.count("}")
                        open_brackets = code_content.count("[") - code_content.count("]")
                        fixed = code_content
                        if open_braces > 0:
                            fixed += "\n" + "}" * open_braces
                        if open_brackets > 0:
                            fixed += "\n" + "]" * open_brackets
                        obj = json.loads(fixed)
                        return obj if isinstance(obj, dict) else None
                    except Exception:
                        pass
            
            # Try to find JSON object in the code block content
            # Look for the first { that starts a JSON object
            json_start = code_content.find("{")
            if json_start != -1:
                # Use brace matching to find the complete JSON object
                brace_count = 0
                in_string = False
                escape_next = False
                json_end = json_start
                
                for i in range(json_start, len(code_content)):
                    char = code_content[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == "\\":
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i
                                break
                
                if json_end > json_start:
                    json_str = code_content[json_start : json_end + 1]
                    # Try parsing as-is first
                    try:
                        obj = json.loads(json_str)
                        return obj if isinstance(obj, dict) else None
                    except json.JSONDecodeError:
                        # Try to fix incomplete JSON
                        try:
                            open_braces = json_str.count("{") - json_str.count("}")
                            open_brackets = json_str.count("[") - json_str.count("]")
                            fixed = json_str
                            if open_braces > 0:
                                fixed += "\n" + "}" * open_braces
                            if open_brackets > 0:
                                fixed += "\n" + "]" * open_brackets
                            obj = json.loads(fixed)
                            return obj if isinstance(obj, dict) else None
                        except Exception:
                            pass

    # Try to find JSON object by matching braces more carefully
    # This handles both code-blocked and raw JSON
    start = s.find("{")
    if start != -1:
        brace_count = 0
        end = start
        in_string = False
        escape_next = False
        
        for i in range(start, len(s)):
            char = s[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == "\\":
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
        
        if end > start:
            try:
                json_str = s[start : end + 1]
                obj = json.loads(json_str)
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError as e:
                # If incomplete, try to close it
                try:
                    open_braces = json_str.count("{") - json_str.count("}")
                    open_brackets = json_str.count("[") - json_str.count("]")
                    fixed = json_str
                    if open_braces > 0:
                        fixed += "\n" + "}" * open_braces
                    if open_brackets > 0:
                        fixed += "\n" + "]" * open_brackets
                    obj = json.loads(fixed)
                    return obj if isinstance(obj, dict) else None
                except Exception:
                    pass
            except Exception:
                pass
    
    # Last resort: scanning
    for i, char in enumerate(s):
        if char == "{":
            brace_count = 0
            for j in range(i, len(s)):
                if s[j] == "{":
                    brace_count += 1
                elif s[j] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            json_str = s[i : j + 1]
                            obj = json.loads(json_str)
                            return obj if isinstance(obj, dict) else None
                        except json.JSONDecodeError:
                            # Try to fix incomplete JSON
                            try:
                                open_braces = json_str.count("{") - json_str.count("}")
                                open_brackets = json_str.count("[") - json_str.count("]")
                                fixed = json_str
                                if open_braces > 0:
                                    fixed += "\n" + "}" * open_braces
                                if open_brackets > 0:
                                    fixed += "\n" + "]" * open_brackets
                                obj = json.loads(fixed)
                                return obj if isinstance(obj, dict) else None
                            except Exception:
                                break
                        except Exception:
                            break
            break  # Only try the first opening brace
    
    return None
