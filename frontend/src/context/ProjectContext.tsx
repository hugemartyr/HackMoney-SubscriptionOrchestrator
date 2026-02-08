'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { FileSystemNode, AuditResult, DiffData } from '@/lib/types';

interface ProjectState {
  isUploaded: boolean;
  projectName: string | null;
  activeRunId: string | null;
  fileTree: FileSystemNode | null;
  openFiles: string[];
  currentFile: string | null;
  fileContents: Record<string, string>;
  draftContents: Record<string, string>;
  dirtyFiles: Record<string, boolean>;
  terminalLogs: string[];
  auditResult: AuditResult | null;
  pendingDiffs: Record<string, DiffData>;
  buildStatus: 'idle' | 'building' | 'success' | 'error';
  buildOutput: string;
  approvalPending: boolean;
  approvalFiles: string[];
}

interface ProjectContextType {
  state: ProjectState;
  setState: React.Dispatch<React.SetStateAction<ProjectState>>;
  setActiveRunId: (runId: string | null) => void;
  updateFileTree: (tree: FileSystemNode) => void;
  updateFileContent: (path: string, content: string) => void;
  updateDraftContent: (path: string, content: string) => void;
  markFileSaved: (path: string, content: string) => void;
  addTerminalLog: (line: string) => void;
  setAuditResult: (result: AuditResult | null) => void;
  addPendingDiff: (diff: DiffData) => void;
  removePendingDiff: (file: string) => void;
  clearPendingDiffs: () => void;
  setBuildStatus: (status: 'idle' | 'building' | 'success' | 'error', output?: string) => void;
  setCurrentFile: (path: string | null) => void;
  openFile: (path: string) => void;
  closeFile: (path: string) => void;
  markProjectUploaded: (name: string) => void;
  setApprovalPending: (pending: boolean) => void;
  setApprovalFiles: (files: string[]) => void;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

const initialState: ProjectState = {
  isUploaded: false,
  projectName: null,
  activeRunId: null,
  fileTree: null,
  openFiles: [],
  currentFile: null,
  fileContents: {},
  draftContents: {},
  dirtyFiles: {},
  terminalLogs: [],
  auditResult: null,
  pendingDiffs: {},
  buildStatus: 'idle',
  buildOutput: '',
  approvalPending: false,
  approvalFiles: [],
};

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ProjectState>(initialState);

  const setActiveRunId = (runId: string | null) => {
    setState(prev => ({ ...prev, activeRunId: runId }));
  };

  const updateFileTree = (tree: FileSystemNode) => {
    setState(prev => ({ ...prev, fileTree: tree }));
  };

  const updateFileContent = (path: string, content: string) => {
    setState(prev => ({
      ...prev,
      fileContents: { ...prev.fileContents, [path]: content },
      // Only overwrite draft if user hasn't edited this file locally.
      draftContents: prev.dirtyFiles[path]
        ? prev.draftContents
        : { ...prev.draftContents, [path]: content },
    }));
  };

  const updateDraftContent = (path: string, content: string) => {
    setState(prev => ({
      ...prev,
      draftContents: { ...prev.draftContents, [path]: content },
      dirtyFiles: { ...prev.dirtyFiles, [path]: true },
    }));
  };

  const markFileSaved = (path: string, content: string) => {
    setState(prev => ({
      ...prev,
      fileContents: { ...prev.fileContents, [path]: content },
      draftContents: { ...prev.draftContents, [path]: content },
      dirtyFiles: { ...prev.dirtyFiles, [path]: false },
    }));
  };

  const addTerminalLog = (line: string) => {
    setState(prev => ({
      ...prev,
      terminalLogs: [...prev.terminalLogs, line],
    }));
  };

  const setAuditResult = (result: AuditResult | null) => {
    setState(prev => ({ ...prev, auditResult: result }));
  };

  const addPendingDiff = (diff: DiffData) => {
    setState(prev => ({
      ...prev,
      pendingDiffs: { ...prev.pendingDiffs, [diff.file]: diff },
    }));
  };

  const removePendingDiff = (file: string) => {
    setState(prev => {
      const { [file]: _, ...remainingDiffs } = prev.pendingDiffs;
      return { ...prev, pendingDiffs: remainingDiffs };
    });
  };

  const clearPendingDiffs = () => {
    setState(prev => ({ ...prev, pendingDiffs: {} }));
  };

  const setBuildStatus = (status: 'idle' | 'building' | 'success' | 'error', output: string = '') => {
    setState(prev => ({
      ...prev,
      buildStatus: status,
      buildOutput: output,
    }));
  };

  const setCurrentFile = (path: string | null) => {
    setState(prev => ({ ...prev, currentFile: path }));
  };

  const openFile = (path: string) => {
    setState(prev => {
      const openFiles = prev.openFiles.includes(path)
        ? prev.openFiles
        : [...prev.openFiles, path];
      return { ...prev, openFiles, currentFile: path };
    });
  };

  const closeFile = (path: string) => {
    setState(prev => {
      if (!prev.openFiles.includes(path)) return prev;

      const idx = prev.openFiles.indexOf(path);
      const openFiles = prev.openFiles.filter(p => p !== path);

      let currentFile = prev.currentFile;
      if (prev.currentFile === path) {
        // Switch to neighbor tab if possible
        if (openFiles.length === 0) {
          currentFile = null;
        } else if (idx - 1 >= 0) {
          currentFile = openFiles[Math.min(idx - 1, openFiles.length - 1)];
        } else {
          currentFile = openFiles[0];
        }
      }

      // Clean up per-file state to avoid leaks
      const { [path]: _c, ...fileContents } = prev.fileContents;
      const { [path]: _d, ...draftContents } = prev.draftContents;
      const { [path]: _f, ...dirtyFiles } = prev.dirtyFiles;

      return { ...prev, openFiles, currentFile, fileContents, draftContents, dirtyFiles };
    });
  };

  const markProjectUploaded = (name: string) => {
    setState(prev => ({ ...prev, isUploaded: true, projectName: name }));
  };

  const setApprovalPending = (pending: boolean) => {
    setState(prev => ({ ...prev, approvalPending: pending }));
  };

  const setApprovalFiles = (files: string[]) => {
    setState(prev => ({ ...prev, approvalFiles: files }));
  };

  const value: ProjectContextType = {
    state,
    setState,
    setActiveRunId,
    updateFileTree,
    updateFileContent,
    updateDraftContent,
    markFileSaved,
    addTerminalLog,
    setAuditResult,
    addPendingDiff,
    removePendingDiff,
    clearPendingDiffs,
    setBuildStatus,
    setCurrentFile,
    openFile,
    closeFile,
    markProjectUploaded,
    setApprovalPending,
    setApprovalFiles,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjectContext() {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error('useProjectContext must be used within a ProjectProvider');
  }
  return context;
}
