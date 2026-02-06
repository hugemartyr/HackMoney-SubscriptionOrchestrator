# JSON Extraction Fix for Markdown Code Blocks

## Problem

The LLM (Google Gemini) returns valid JSON wrapped in markdown code blocks:

```json
{
  "diffs": [...]
}
```

The parser was failing because it was attempting to parse the entire response (including the markdown) as JSON.

## Root Cause

In `backend/agent/llm/utils.py`, the `extract_json_from_response()` function had the wrong priority:

1. ❌ Try parsing entire response as JSON (fails because of markdown wrapper)
2. Try markdown code block extraction (skipped due to early failure)

## Solution

Reordered extraction priorities in `extract_json_from_response()`:

### New Priority Order:

1. **Priority 1** ✅ Extract from markdown code blocks (`json...`)
   - Handles: `\`\`\`json\n{...}\n\`\`\``
   - Handles incomplete: `\`\`\`json\n{...}` (no closing \`\`\`)
   - Applies brace matching to find complete JSON object

2. **Priority 2** Try parsing entire string as JSON
   - Handles: Raw JSON responses without markdown
   - Attempts to fix truncated JSON by closing braces

3. **Priority 3** Brace matching fallback
   - Finds first `{` and matches to closing `}`
   - Last resort for malformed responses

## Files Modified

- `/backend/agent/llm/utils.py` - Reorganized `extract_json_from_response()`

## Testing

The fix now handles:

- ✅ LLM responses wrapped in markdown code blocks
- ✅ Incomplete code blocks (missing closing ```)
- ✅ Raw JSON responses
- ✅ Truncated JSON (auto-closes braces)

## Impact

- Eliminates "No valid JSON response" errors when LLM returns markdown-wrapped JSON
- Maintains backward compatibility with raw JSON responses
- More robust error handling for edge cases
