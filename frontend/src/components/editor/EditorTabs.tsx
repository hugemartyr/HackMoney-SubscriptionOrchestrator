'use client';

import React, { useState } from 'react';
import { Save, X } from 'lucide-react';
import { useProjectContext } from '@/context/ProjectContext';
import { putFileContent } from '@/lib/api';

function basename(path: string) {
  const parts = path.split('/');
  return parts[parts.length - 1] || path;
}

export default function EditorTabs() {
  const { state, openFile, closeFile, markFileSaved } = useProjectContext();
  const [saving, setSaving] = useState<Record<string, boolean>>({});

  if (state.openFiles.length === 0) return null;

  return (
    <div className="h-10 flex items-center bg-gray-950 border-b border-gray-800 overflow-x-auto">
      {state.openFiles.map((path) => {
        const isActive = state.currentFile === path;
        const isDirty = !!state.dirtyFiles[path];
        return (
          <div
            key={path}
            className={
              'flex items-center gap-2 px-3 h-full border-r border-gray-800 cursor-pointer select-none whitespace-nowrap ' +
              (isActive ? 'bg-gray-900 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-900/50')
            }
            onClick={() => openFile(path)}
            title={path}
          >
            <span className="text-xs font-mono flex items-center gap-2">
              <span>{basename(path)}</span>
              {isDirty && <span className="inline-block w-2 h-2 rounded-full bg-yellow-400" title="Unsaved changes" />}
            </span>

            {isDirty && (
              <button
                className="p-1 rounded hover:bg-gray-800"
                onClick={async (e) => {
                  e.stopPropagation();
                  if (saving[path]) return;
                  try {
                    setSaving((prev) => ({ ...prev, [path]: true }));
                    const content = state.draftContents[path] ?? state.fileContents[path] ?? '';
                    await putFileContent(path, content);
                    markFileSaved(path, content);
                  } finally {
                    setSaving((prev) => ({ ...prev, [path]: false }));
                  }
                }}
                aria-label={`Save ${basename(path)}`}
                title="Save"
              >
                <Save size={14} className={saving[path] ? 'opacity-50' : ''} />
              </button>
            )}

            <button
              className="p-1 rounded hover:bg-gray-800"
              onClick={(e) => {
                e.stopPropagation();
                closeFile(path);
              }}
              aria-label={`Close ${basename(path)}`}
              title="Close"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

