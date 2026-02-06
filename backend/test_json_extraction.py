#!/usr/bin/env python3
"""
Quick test for JSON extraction from markdown code blocks.
"""
from agent.llm.utils import extract_json_from_response

# Test case from the error message
test_response = '''```json
{
  "diffs": [
    {
      "file": "package.json",
      "oldCode": "test",
      "newCode": "updated"
    }
  ]
}
```
'''

result = extract_json_from_response(test_response)
if result:
    print("✅ Successfully extracted JSON from markdown code block")
    print(f"   Keys: {list(result.keys())}")
    print(f"   Has 'diffs': {'diffs' in result}")
else:
    print("❌ Failed to extract JSON")

# Test raw JSON
raw_json = '{"diffs": [], "test": true}'
result2 = extract_json_from_response(raw_json)
if result2:
    print("✅ Successfully extracted raw JSON")
else:
    print("❌ Failed to extract raw JSON")

# Test JSON in code block without closing ```
incomplete_block = '''```json
{"changes": [{"file": "app.ts", "search": "old", "replace": "new"}]}
'''
result3 = extract_json_from_response(incomplete_block)
if result3:
    print("✅ Successfully extracted JSON from incomplete code block")
else:
    print("❌ Failed to extract JSON from incomplete block")
