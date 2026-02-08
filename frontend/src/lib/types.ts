// SSE Event Types
export interface RunStartedEvent {
  type: 'run_started';
  runId: string;
  prompt: string;
}

export interface RunFinishedEvent {
  type: 'run_finished';
  runId: string;
  /** True when paused for HITL approval; frontend keeps activeRunId for resume */
  interrupted?: boolean;
}

export interface ThoughtEvent {
  type: 'thought';
  runId?: string;
  content: string;
}

export interface ToolStartEvent {
  type: 'tool_start';
  runId: string;
  name: string;
}

export interface ToolEndEvent {
  type: 'tool_end';
  runId: string;
  name: string;
  status: 'success' | 'error';
}

export interface FileTreeEvent {
  type: 'file_tree';
  runId?: string;
  tree: FileSystemNode;
}

export interface FileContentEvent {
  type: 'file_content';
  runId?: string;
  path: string;
  content: string;
}

export interface TerminalEvent {
  type: 'terminal';
  runId?: string;
  line: string;
}

export interface AuditEvent {
  type: 'audit';
  runId?: string;
  analysis: AuditResult;
}

export interface DiffEvent {
  type: 'diff';
  runId?: string;
  file: string;
  oldCode: string;
  newCode: string;
}

export interface ProposedFileEvent {
  type: 'proposed_file';
  runId: string;
  path: string;
  content: string;
}

export interface AwaitingUserReviewEvent {
  type: 'awaiting_user_review';
  runId: string;
  files: string[];
}

export interface BuildEvent {
  type: 'build';
  runId?: string;
  status: 'start' | 'output' | 'success' | 'error';
  data?: string;
}

export interface CodeUpdateEvent {
  type: 'code_update';
  content: string;
}

export type SSEEvent = 
  | RunStartedEvent
  | RunFinishedEvent
  | ThoughtEvent 
  | ToolStartEvent
  | ToolEndEvent
  | FileTreeEvent 
  | FileContentEvent 
  | TerminalEvent 
  | AuditEvent 
  | DiffEvent 
  | ProposedFileEvent
  | AwaitingUserReviewEvent
  | BuildEvent 
  | CodeUpdateEvent;

// File System Types
export interface FileSystemNode {
  path: string;
  name: string;
  type: 'file' | 'folder';
  children?: FileSystemNode[];
}

// Audit Result
export interface AuditResult {
  framework: string;
  currentPayment: string;
  proposedChanges: string[];
  feeSavings: string;
}

// Diff Data
export interface DiffData {
  file: string;
  oldCode: string;
  newCode: string;
}
