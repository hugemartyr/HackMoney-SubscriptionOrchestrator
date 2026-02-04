// SSE Event Types
export interface ThoughtEvent {
  type: 'thought';
  content: string;
}

export interface ToolEvent {
  type: 'tool';
  name: string;
  status: string;
}

export interface FileTreeEvent {
  type: 'file_tree';
  tree: FileSystemNode;
}

export interface FileContentEvent {
  type: 'file_content';
  path: string;
  content: string;
}

export interface TerminalEvent {
  type: 'terminal';
  line: string;
}

export interface AuditEvent {
  type: 'audit';
  analysis: AuditResult;
}

export interface DiffEvent {
  type: 'diff';
  file: string;
  oldCode: string;
  newCode: string;
}

export interface BuildEvent {
  type: 'build';
  status: 'start' | 'output' | 'success' | 'error';
  data?: string;
}

export interface CodeUpdateEvent {
  type: 'code_update';
  content: string;
}

export type SSEEvent = 
  | ThoughtEvent 
  | ToolEvent 
  | FileTreeEvent 
  | FileContentEvent 
  | TerminalEvent 
  | AuditEvent 
  | DiffEvent 
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
