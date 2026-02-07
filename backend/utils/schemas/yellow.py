from pydantic import BaseModel
from typing import Dict, Any, Optional, List


class YellowInitializerInput(BaseModel):
    """Input schema for the Yellow SDK initializer tool."""
    repo_path: str
    framework_hint: Optional[str] = None


class YellowInitializerOutput(BaseModel):
    """Output schema for tool responses."""
    success: bool
    framework_detected: str
    steps_completed: Dict[str, bool]
    files_modified: list[str]
    diffs: list[Dict[str, Any]] = []
    message: str
    error: Optional[str] = None


class YellowNetworkWorkflowInput(BaseModel):
    repo_path: str
    framework_hint: Optional[str] = None


class YellowNetworkWorkflowOutput(BaseModel):
    success: bool
    wallet_address: Optional[str] = None
    workflow_output: Optional[str] = None
    files_modified: List[str] = []
    diffs: List[Dict[str, Any]] = []
    message: str
    error: Optional[str] = None


class YellowVersionedIntegrationInput(BaseModel):
    """Input for versioned integration tool."""
    repo_path: str
    framework_hint: Optional[str] = None
    requires_versioned: bool = False


class YellowVersionedIntegrationOutput(BaseModel):
    """Output from versioned integration execution."""
    success: bool
    action: Optional[str] = None  # installed, already_up_to_date, upgraded
    version: str
    files_modified: List[str] = []
    diffs: List[Dict[str, Any]] = []
    message: str
    error: Optional[str] = None


class YellowMultiPartyInput(BaseModel):
    """Input for multiparty workflow tool."""
    repo_path: str
    framework_hint: Optional[str] = None
    requires_multiparty: bool = False


class YellowMultiPartyOutput(BaseModel):
    """Output from multiparty workflow execution."""
    success: bool
    route_created: Optional[str] = None
    files_modified: List[str] = []
    diffs: List[Dict[str, Any]] = []
    message: str
    error: Optional[str] = None
