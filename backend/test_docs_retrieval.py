#!/usr/bin/env python3
"""
Test script to verify that the retrieve_docs functionality is working properly.

This script tests:
1. Vector database initialization (GOOGLE_API_KEY, ChromaDB accessibility)
2. Search execution (retrieve_docs_node functionality)
3. Routing logic (when retrieve_docs should be called)

Run from backend/ directory:
    python test_docs_retrieval.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add backend to path so we can import modules
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Load environment variables if .env exists
try:
    from utils.dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(f"⚠️  Warning: Could not load .env file: {e}")

from config import settings
from agent.tools.vector_store import YellowVectorStore
from utils.helper_functions import _search_docs_wrapper
from agent.state import AgentState


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print a test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")


def test_1_google_api_key():
    """Test 1: Check if GOOGLE_API_KEY is set."""
    print_section("Test 1: GOOGLE_API_KEY Configuration")
    
    api_key = settings.GOOGLE_API_KEY
    api_key_from_env = os.getenv("GOOGLE_API_KEY")
    
    if api_key:
        print_result("GOOGLE_API_KEY is set", True, f"Length: {len(api_key)} characters")
        if api_key.startswith("AIza"):
            print("   ✓ Key format looks correct (starts with 'AIza')")
        else:
            print("   ⚠️  Key format may be unexpected")
        return True
    else:
        print_result("GOOGLE_API_KEY is set", False, "GOOGLE_API_KEY is not set in environment")
        print("   💡 Set GOOGLE_API_KEY environment variable or add it to .env file")
        return False


def test_2_chromadb_initialization():
    """Test 2: Check if ChromaDB can be initialized."""
    print_section("Test 2: ChromaDB Initialization")
    
    try:
        vs = YellowVectorStore()
        print_result("YellowVectorStore initialization", True, "Successfully created instance")
        
        # Check persist directory
        persist_dir = Path(vs.persist_directory)
        if persist_dir.exists():
            print_result("ChromaDB persist directory exists", True, f"Path: {persist_dir}")
            
            # Check if database files exist
            db_files = list(persist_dir.glob("*.sqlite3"))
            if db_files:
                print_result("ChromaDB database files found", True, f"Found {len(db_files)} database file(s)")
            else:
                print_result("ChromaDB database files found", False, "No .sqlite3 files found - database may be empty")
                print("   💡 Run vector_db_setup/load_enriched_to_vector_db.py to populate the database")
        else:
            print_result("ChromaDB persist directory exists", False, f"Directory not found: {persist_dir}")
            print("   💡 Directory will be created on first use")
        
        return True, vs
        
    except ValueError as e:
        if "GOOGLE_API_KEY" in str(e):
            print_result("YellowVectorStore initialization", False, "GOOGLE_API_KEY not set")
            return False, None
        else:
            print_result("YellowVectorStore initialization", False, f"ValueError: {e}")
            return False, None
    except Exception as e:
        print_result("YellowVectorStore initialization", False, f"Unexpected error: {type(e).__name__}: {e}")
        import traceback
        print(f"   Traceback:\n{traceback.format_exc()}")
        return False, None


def test_3_chromadb_collection():
    """Test 3: Check if ChromaDB collection exists and has documents."""
    print_section("Test 3: ChromaDB Collection Check")
    
    try:
        vs = YellowVectorStore()
        
        # Try to get collection info
        collection = vs.vector_store._collection
        if collection:
            count = collection.count()
            print_result("Collection 'yellow_docs' exists", True, f"Document count: {count}")
            
            if count > 0:
                print_result("Collection has documents", True, f"{count} documents available")
                return True, vs
            else:
                print_result("Collection has documents", False, "Collection is empty")
                print("   💡 Run vector_db_setup/load_enriched_to_vector_db.py to populate the database")
                return False, vs
        else:
            print_result("Collection 'yellow_docs' exists", False, "Could not access collection")
            return False, vs
            
    except Exception as e:
        print_result("Collection check", False, f"Error: {type(e).__name__}: {e}")
        import traceback
        print(f"   Traceback:\n{traceback.format_exc()}")
        return False, None


def test_4_search_functionality():
    """Test 4: Test search functionality with sample queries."""
    print_section("Test 4: Search Functionality")
    
    try:
        vs = YellowVectorStore()
        
        # Test queries
        test_queries = [
            "create payment session",
            "Yellow Network SDK",
            "state channel",
            "nitrolite",
        ]
        
        all_passed = True
        for query in test_queries:
            try:
                results = vs.search(query, k=3)
                if results and len(results.strip()) > 0:
                    result_len = len(results)
                    print_result(f"Search query: '{query}'", True, f"Returned {result_len} characters")
                    # Show first 200 chars of result
                    preview = results[:200].replace("\n", " ")
                    print(f"   Preview: {preview}...")
                else:
                    print_result(f"Search query: '{query}'", False, "Returned empty result")
                    all_passed = False
            except Exception as e:
                print_result(f"Search query: '{query}'", False, f"Error: {type(e).__name__}: {e}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_result("Search functionality", False, f"Error: {type(e).__name__}: {e}")
        import traceback
        print(f"   Traceback:\n{traceback.format_exc()}")
        return False


def test_5_search_docs_wrapper():
    """Test 5: Test _search_docs_wrapper function (used by retrieve_docs_node)."""
    print_section("Test 5: _search_docs_wrapper Function")
    
    test_cases = [
        {
            "query": "create payment session",
            "missing_info": None,
            "description": "Basic query without missing_info"
        },
        {
            "query": "Yellow Network",
            "missing_info": ["SDK integration", "state channels"],
            "description": "Query with missing_info"
        },
    ]
    
    all_passed = True
    for case in test_cases:
        try:
            result = _search_docs_wrapper(case["query"], case["missing_info"])
            
            if result.startswith("Error"):
                print_result(f"Wrapper: {case['description']}", False, f"Error returned: {result}")
                all_passed = False
            elif len(result.strip()) > 0:
                print_result(f"Wrapper: {case['description']}", True, f"Returned {len(result)} characters")
            else:
                print_result(f"Wrapper: {case['description']}", False, "Returned empty result")
                all_passed = False
                
        except Exception as e:
            print_result(f"Wrapper: {case['description']}", False, f"Exception: {type(e).__name__}: {e}")
            all_passed = False
    
    return all_passed


def test_6_retrieve_docs_node_simulation():
    """Test 6: Simulate retrieve_docs_node execution."""
    print_section("Test 6: retrieve_docs_node Simulation")
    
    import asyncio
    
    async def simulate_retrieve_docs_node():
        """Simulate the actual retrieve_docs_node logic."""
        state: AgentState = {
            "prompt": "I want to integrate Yellow Network SDK for payments",
            "missing_info": ["payment integration", "SDK setup"],
            "docs_retrieved": False,
            "doc_context": "",
        }
        
        try:
            # This is the exact logic from retrieve_docs_node
            docs = await asyncio.to_thread(
                _search_docs_wrapper,
                state.get("prompt", ""),
                state.get("missing_info", [])
            )
            
            state["docs_retrieved"] = True
            state["doc_context"] = docs
            
            if docs.startswith("Error"):
                print_result("retrieve_docs_node simulation", False, f"Error: {docs}")
                return False, state
            elif len(docs.strip()) > 0:
                print_result("retrieve_docs_node simulation", True, f"Retrieved {len(docs)} characters")
                print(f"   doc_context preview: {docs[:300]}...")
                return True, state
            else:
                print_result("retrieve_docs_node simulation", False, "Empty doc_context returned")
                return False, state
                
        except Exception as e:
            print_result("retrieve_docs_node simulation", False, f"Exception: {type(e).__name__}: {e}")
            import traceback
            print(f"   Traceback:\n{traceback.format_exc()}")
            return False, state
    
    try:
        passed, final_state = asyncio.run(simulate_retrieve_docs_node())
        return passed
    except Exception as e:
        print_result("retrieve_docs_node simulation", False, f"Failed to run: {type(e).__name__}: {e}")
        return False


def test_7_routing_logic():
    """Test 7: Analyze routing logic to see when retrieve_docs would be called."""
    print_section("Test 7: Routing Logic Analysis")
    
    # Simulate different state scenarios
    scenarios = [
        {
            "name": "Scenario 1: No files, no docs retrieved",
            "state": {
                "context_ready": False,
                "context_loop_count": 1,
                "files_to_read": [],
                "file_contents": {},
                "missing_info": ["documentation", "API reference"],
                "docs_retrieved": False,
            },
            "expected": "retrieve_docs",
        },
        {
            "name": "Scenario 2: Has files_to_read (should prioritize read_code)",
            "state": {
                "context_ready": False,
                "context_loop_count": 1,
                "files_to_read": ["package.json", "src/main.ts"],
                "file_contents": {},
                "missing_info": ["documentation"],
                "docs_retrieved": False,
            },
            "expected": "read_code",  # This is why retrieve_docs might be skipped!
        },
        {
            "name": "Scenario 3: Has file_contents, no docs yet",
            "state": {
                "context_ready": False,
                "context_loop_count": 1,
                "files_to_read": [],
                "file_contents": {"package.json": "{}"},
                "missing_info": ["Yellow SDK documentation"],
                "docs_retrieved": False,
            },
            "expected": "retrieve_docs",
        },
        {
            "name": "Scenario 4: Loop count exceeded (should force ready)",
            "state": {
                "context_ready": False,
                "context_loop_count": 5,  # > 4
                "files_to_read": [],
                "file_contents": {},
                "missing_info": ["documentation"],
                "docs_retrieved": False,
            },
            "expected": "ready",
        },
    ]
    
    # Import routing function
    from agent.graph import route_context_decision
    
    all_correct = True
    for scenario in scenarios:
        decision = route_context_decision(scenario["state"])
        is_correct = decision == scenario["expected"]
        
        status = "✅" if is_correct else "❌"
        print(f"{status} {scenario['name']}")
        print(f"   Expected: {scenario['expected']}, Got: {decision}")
        
        if not is_correct:
            all_correct = False
            print(f"   ⚠️  Routing mismatch!")
        
        # Highlight the issue
        if scenario["name"] == "Scenario 2" and decision == "read_code":
            print("   💡 ISSUE: When files_to_read exists, retrieve_docs is skipped!")
            print("      This might be why docs aren't being retrieved.")
    
    return all_correct


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  DOCS RETRIEVAL SYSTEM TEST SUITE")
    print("=" * 80)
    
    results = {}
    
    # Test 1: API Key
    results["api_key"] = test_1_google_api_key()
    
    # Test 2: ChromaDB Initialization
    init_passed, vs = test_2_chromadb_initialization()
    results["chromadb_init"] = init_passed
    
    if not init_passed:
        print("\n⚠️  Cannot continue with remaining tests - ChromaDB initialization failed")
        print_summary(results)
        return
    
    # Test 3: Collection Check
    collection_passed, vs = test_3_chromadb_collection()
    results["chromadb_collection"] = collection_passed
    
    # Test 4: Search
    results["search"] = test_4_search_functionality()
    
    # Test 5: Wrapper
    results["wrapper"] = test_5_search_docs_wrapper()
    
    # Test 6: Node Simulation
    results["node_simulation"] = test_6_retrieve_docs_node_simulation()
    
    # Test 7: Routing
    results["routing"] = test_7_routing_logic()
    
    # Summary
    print_summary(results)


def print_summary(results: Dict[str, bool]):
    """Print test summary."""
    print_section("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    print("\nDetailed Results:")
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}")
    
    # Key findings
    print("\n" + "=" * 80)
    print("  KEY FINDINGS")
    print("=" * 80)
    
    if not results.get("api_key"):
        print("❌ GOOGLE_API_KEY is not set - this will prevent all docs retrieval")
        print("   Fix: Set GOOGLE_API_KEY environment variable")
    
    if not results.get("chromadb_collection"):
        print("❌ ChromaDB collection is empty - no documents to retrieve")
        print("   Fix: Run: python vector_db_setup/load_enriched_to_vector_db.py")
    
    if not results.get("routing"):
        print("⚠️  Routing logic may skip retrieve_docs when files_to_read exists")
        print("   This is by design, but may prevent docs from being retrieved")
    
    if all(results.values()):
        print("✅ All tests passed! Docs retrieval should work properly.")
    else:
        print("❌ Some tests failed. Review the issues above.")


if __name__ == "__main__":
    main()
