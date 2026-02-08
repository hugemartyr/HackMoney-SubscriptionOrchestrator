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
    print("🚀 Starting Agent Flow Test...")
    
    # Initial state
    initial_state: AgentState = {
        "prompt": "Integrate Yellow Network SDK to show a widget on the home page.",
        "file_contents": {}, # Start empty to force read_code
        "session_memory": [],
        "thinking_log": [],
        "context_ready": False,
        "docs_retrieved": False,
        "awaiting_approval": False,
        "build_success": False,
        "error_count": 0
    }

    # Run the graph
    print(f"Input Prompt: {initial_state['prompt']}\n")
    
    current_state = initial_state.copy()
    approval_pending = False
    
    async for event in app_graph.astream(initial_state):
        for node_name, state_update in event.items():
            # Merge state updates
            current_state.update(state_update)
            
            print(f"\n--- Node: {node_name} ---")
            
            if "thinking_log" in state_update and state_update["thinking_log"]:
                print(f"Thinking: {state_update['thinking_log'][-1]}")
            
            if "plan_notes" in state_update:
                print(f"Plan: {state_update['plan_notes'][:100]}...")
            
            if "diffs" in state_update:
                print(f"Generated {len(state_update['diffs'])} diffs.")
                for d in state_update['diffs']:
                    print(f"  - {d['file']}")
            
            if "pending_approval_files" in state_update:
                files = state_update.get("pending_approval_files", [])
                print(f"Pending approval for {len(files)} files: {', '.join(files)}")

            if "terminal_output" in state_update:
                output = state_update.get("terminal_output", [])
                if output:
                    print(f"Terminal output ({len(output)} lines): {output[-1][:80]}...")

            if "build_output" in state_update:
                output = state_update.get("build_output", "")
                if output:
                    print(f"Build Output: {output[:100]}...")
            
            if "error_analysis" in state_update:
                analysis = state_update.get("error_analysis", {})
                if analysis:
                    print(f"Error Analysis: {analysis.get('error_type', 'unknown')} - {analysis.get('root_cause', '')[:80]}...")

            if "final_summary" in state_update:
                print(f"\n=== FINAL SUMMARY ===\n{state_update['final_summary']}")
                
            # Handle approval - auto-approve for testing
            if state_update.get("awaiting_approval") and not approval_pending:
                approval_pending = True
                print("\n>>> Auto-approving for test purposes...")
                print(f">>> Files pending approval: {state_update.get('pending_approval_files', [])}")
                # Break here - the graph will loop on approval, so we stop the test
                # In a real scenario, the runner would pause and wait for user input
                print("🛑 Hit Approval Step. Test stopping here (would wait for user approval in production).")
                print("\n✅ Test completed successfully up to approval step!")
                return

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    except Exception as e:
        print(f"\nTest failed: {e}")
