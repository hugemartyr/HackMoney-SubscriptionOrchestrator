'use client';

import React, { useEffect, useState } from 'react';
import Editor from "@monaco-editor/react";
import { useEditorContext } from "@/hooks/useEditorContext";
import { useProjectContext } from '@/context/ProjectContext';
import EditorTabs from '@/components/editor/EditorTabs';

export default function YellowEditor() {
  const { handleEditorDidMount } = useEditorContext();
  const { state, updateDraftContent } = useProjectContext();
  const [isAgentEditing, setIsAgentEditing] = useState(false);

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
        <div className="px-4 py-2 bg-yellow-500/20 border-b border-yellow-500/50 text-yellow-400 text-xs font-semibold">
          Agent is editing this file...
        </div>
      )}
      {state.currentFile && (
        <div className="px-4 py-1 bg-gray-900 border-b border-gray-800 text-xs text-gray-400 font-mono">
          {state.currentFile}
        </div>
      )}
      <div className="flex-1 min-h-0">
        <Editor 
          height="100%" 
          language={getLanguage(state.currentFile)}
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
            readOnly: false, // Allow user edits if needed
          }}
        />
      </div>
    </div>
  );
}
