'use client';

import React, { useEffect, useRef, useState } from 'react';
import Editor, { DiffEditor } from '@monaco-editor/react';
import { useEditorContext } from "@/hooks/useEditorContext";
import { useProjectContext } from '@/context/ProjectContext';
import EditorTabs from '@/components/editor/EditorTabs';

export default function YellowEditor() {
  const { handleEditorDidMount } = useEditorContext();
  const { state, updateDraftContent } = useProjectContext();
  const [isAgentEditing, setIsAgentEditing] = useState(false);
  const currentFileRef = useRef<string | null>(null);
  currentFileRef.current = state.currentFile ?? null;

  const isDiffTab = !!state.currentFile?.startsWith('__diff__/');
  const diffTarget = isDiffTab ? state.currentFile?.slice('__diff__/'.length) : null;
  const pendingDiff = diffTarget ? state.pendingDiffs[diffTarget] : null;
  const showDiffView = isDiffTab && diffTarget && pendingDiff != null;

  // Update editor content when file is selected or content changes
  useEffect(() => {
    if (state.currentFile && state.fileContents[state.currentFile]) {
      setIsAgentEditing(true);
      // Reset indicator after a short delay
      setTimeout(() => setIsAgentEditing(false), 2000);
    } else {
      // no-op
    }
  }, [state.currentFile, state.fileContents]);

  // Determine language from file extension
  const getLanguage = (filePath: string | null): string => {
    if (!filePath) return 'typescript';
    const ext = filePath.split('.').pop()?.toLowerCase();
    const langMap: Record<string, string> = {
      'ts': 'typescript',
      'tsx': 'typescript',
      'js': 'javascript',
      'jsx': 'javascript',
      'json': 'json',
      'css': 'css',
      'html': 'html',
      'py': 'python',
      'md': 'markdown',
    };
    return langMap[ext || ''] || 'typescript';
  };

  return (
    <div className="h-full w-full flex flex-col">
      <EditorTabs />
      {isAgentEditing && (
        <div className="px-4 py-2 bg-primary/20 border-b border-primary/50 text-emerald-glow text-xs font-semibold">
          Agent is editing this file...
        </div>
      )}
      {isDiffTab && diffTarget && (
        <div className="px-4 py-2 bg-blue-500/10 border-b border-blue-500/40 text-blue-300 text-xs">
          Reviewing agent diff for: <span className="font-mono text-blue-200">{diffTarget}</span> (apply/discard from the tab)
        </div>
      )}
      {state.currentFile && (
        <div className="px-4 py-1 bg-gray-900 border-b border-gray-800 text-xs text-gray-400 font-mono">
          {isDiffTab && diffTarget ? diffTarget : state.currentFile}
        </div>
      )}
      <div className="flex-1 min-h-0">
        {showDiffView ? (
          <DiffEditor
            height="100%"
            language={getLanguage(diffTarget)}
            original={pendingDiff!.oldCode ?? ''}
            modified={
              state.currentFile
                ? (state.draftContents[state.currentFile] ??
                  state.fileContents[state.currentFile] ??
                  '')
                : ''
            }
            theme="vs-dark"
            options={{
              renderSideBySide: true,
              readOnly: false,
              automaticLayout: true,
              minimap: { enabled: false },
              fontSize: 14,
              scrollBeyondLastLine: false,
            }}
            onMount={(diffEditor) => {
              const modifiedEditor = diffEditor.getModifiedEditor();
              modifiedEditor.getModel()?.onDidChangeContent(() => {
                const path = currentFileRef.current;
                if (path) {
                  const value = modifiedEditor.getValue();
                  updateDraftContent(path, value);
                }
              });
            }}
          />
        ) : (
          <Editor
            height="100%"
            language={getLanguage(isDiffTab && diffTarget ? diffTarget : state.currentFile)}
            value={
              state.currentFile
                ? (state.draftContents[state.currentFile] ??
                  state.fileContents[state.currentFile] ??
                  "// File content loading...")
                : "// Select a file from the explorer..."
            }
            onChange={(val) => {
              if (!state.currentFile) return;
              updateDraftContent(state.currentFile, val || "");
            }}
            theme="vs-dark"
            onMount={handleEditorDidMount}
            options={{
              automaticLayout: true,
              minimap: { enabled: false },
              fontSize: 14,
              scrollBeyondLastLine: false,
              readOnly: false,
            }}
          />
        )}
      </div>
    </div>
  );
}
