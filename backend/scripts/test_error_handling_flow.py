import asyncio
import os
import sys
from pprint import pprint

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.dotenv import load_dotenv
load_dotenv()

from agent.graph import app_graph
from agent.state import AgentState

async def run_test():
    print("🚀 Starting Error Handling & Fix Planning Flow Test...")
    print("=" * 60)
    
    # Simulate a state after a failed build
    initial_state: AgentState = {
        "prompt": "Integrate Yellow Network SDK to show a widget on the home page.",
        "file_contents": {
            "package.json": '{\n  "name": "test-app",\n  "dependencies": {}\n}',
            "src/main.ts": "console.log('Hello');\n// Missing Yellow SDK import",
        },
        "session_memory": ["Attempted initial integration"],
        "thinking_log": ["Generated code changes", "Applied changes"],
        "context_ready": True,
        "docs_retrieved": True,
        "awaiting_approval": False,
        "build_success": False,  # Simulate build failure
        "build_output": """npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
npm ERR! 
npm ERR! While resolving: test-app@1.0.0
npm ERR! Found: react@18.2.0
npm ERR! But react@18.2.0 is not compatible with @yellow-network/sdk@1.0.0
npm ERR! 
npm ERR! Fix the upstream dependency conflict, or try again with --force
npm ERR! A complete log of this run can be found in: npm-debug.log""",
        "build_command": "npm install && npm run build",
        "error_count": 0,
        "diffs": [
            {
                "file": "package.json",
                "oldCode": '{\n  "name": "test-app",\n  "dependencies": {}\n}',
                "newCode": '{\n  "name": "test-app",\n  "dependencies": {\n    "@yellow-network/sdk": "^1.0.0"\n  }\n}'
            }
        ]
    }

    print(f"Input Prompt: {initial_state['prompt']}")
    print(f"Simulated Build Output:\n{initial_state['build_output']}\n")
    print("=" * 60)
    
    # Start from error_analysis node by using a custom entry
    # We'll manually invoke the error handling nodes
    from agent.nodes.maintenance import (
        error_analysis_node,
        memory_check_node,
        fix_plan_node,
        escalation_node
    )
    
    current_state = initial_state.copy()
    
    # Test 1: Error Analysis
    print("\n[TEST 1] Error Analysis Node")
    print("-" * 60)
    try:
        error_analysis_result = await error_analysis_node(current_state)
        current_state.update(error_analysis_result)
        
        if "error_analysis" in error_analysis_result:
            analysis = error_analysis_result["error_analysis"]
            print(f"✅ Error Analysis Complete")
            print(f"   Error Type: {analysis.get('error_type', 'unknown')}")
            print(f"   Root Cause: {analysis.get('root_cause', 'N/A')[:100]}...")
            print(f"   Fix Suggestion: {analysis.get('fix_suggestion', 'N/A')[:100]}...")
            if "files_to_fix" in analysis:
                print(f"   Files to Fix: {', '.join(analysis.get('files_to_fix', []))}")
        else:
            print("❌ Error analysis not stored in state")
    except Exception as e:
        print(f"❌ Error Analysis Failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Memory Check
    print("\n[TEST 2] Memory Check Node")
    print("-" * 60)
    try:
        memory_result = await memory_check_node(current_state)
        current_state.update(memory_result)
        error_count = memory_result.get("error_count", 0)
        print(f"✅ Memory Check Complete")
        print(f"   Error Count: {error_count}")
        print(f"   Will {'escalate' if error_count > 3 else 'retry'}")
    except Exception as e:
        print(f"❌ Memory Check Failed: {e}")
        return
    
    # Test 3: Fix Plan (only if error_count <= 3)
    if current_state.get("error_count", 0) <= 3:
        print("\n[TEST 3] Fix Plan Node")
        print("-" * 60)
        try:
            fix_plan_result = await fix_plan_node(current_state)
            current_state.update(fix_plan_result)
            
            if "diffs" in fix_plan_result:
                diffs = fix_plan_result["diffs"]
                print(f"✅ Fix Plan Generated")
                print(f"   Generated {len(diffs)} fix diffs")
                for diff in diffs:
                    print(f"   - {diff.get('file', 'unknown')}")
            else:
                print("⚠️  No diffs generated (may be expected if LLM determines no fixes needed)")
        except Exception as e:
            print(f"❌ Fix Plan Failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[TEST 3] Fix Plan Node - SKIPPED (error_count > 3)")
    
    # Test 4: Escalation (simulate high error count)
    print("\n[TEST 4] Escalation Node")
    print("-" * 60)
    # Temporarily set high error count to test escalation
    escalation_state = current_state.copy()
    escalation_state["error_count"] = 4
    escalation_state["session_memory"] = [
        "Attempted fix 1: Updated package.json",
        "Attempted fix 2: Adjusted dependencies",
        "Attempted fix 3: Tried alternative SDK version"
    ]
    
    try:
        escalation_result = await escalation_node(escalation_state)
        
        if "final_summary" in escalation_result:
            summary = escalation_result["final_summary"]
            print(f"✅ Escalation Complete")
            print(f"   Escalation Message:\n{summary[:300]}...")
        else:
            print("⚠️  Escalation message not in expected format")
    except Exception as e:
        print(f"❌ Escalation Failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Terminal Output Handling
    print("\n[TEST 5] Terminal Output Streaming")
    print("-" * 60)
    from agent.nodes.validation import build_node
    
    # Simulate a build that produces terminal output
    build_test_state: AgentState = {
        "file_contents": {
            "package.json": '{"scripts": {"build": "echo Building..."}}'
        },
        "thinking_log": []
    }
    
    try:
        build_result = await build_node(build_test_state)
        
        if "terminal_output" in build_result:
            terminal_lines = build_result.get("terminal_output", [])
            print(f"✅ Terminal Output Captured")
            print(f"   Captured {len(terminal_lines)} lines")
            if terminal_lines:
                print(f"   Sample output: {terminal_lines[0][:80]}...")
        else:
            print("⚠️  Terminal output not captured")
    except Exception as e:
        print(f"❌ Build Node Test Failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Error Handling Flow Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
