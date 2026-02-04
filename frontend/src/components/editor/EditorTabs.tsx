'use client';

import React, { useState } from 'react';
import { Save, X, Check, Trash2 } from 'lucide-react';
import { useProjectContext } from '@/context/ProjectContext';
import { approveDiff, getFileTree, putFileContent } from '@/lib/api';

function basename(path: string) {
  const parts = path.split('/');
  return parts[parts.length - 1] || path;
}

const DIFF_PREFIX = '__diff__/';

function isDiffTab(path: string) {
  return path.startsWith(DIFF_PREFIX);
}

function originalPathFromDiffTab(path: string) {
  return path.slice(DIFF_PREFIX.length);
}

export default function EditorTabs() {
  const {
    state,
    openFile,
    closeFile,
    markFileSaved,
    updateFileContent,
    updateFileTree,
    removePendingDiff,
  } = useProjectContext();
  const [saving, setSaving] = useState<Record<string, boolean>>({});

  if (state.openFiles.length === 0) return null;

  return (
    <div className="h-10 flex items-center bg-gray-950 border-b border-gray-800 overflow-x-auto">
      {state.openFiles.map((path) => {
        const isActive = state.currentFile === path;
        const isDirty = !!state.dirtyFiles[path];
        const diffTab = isDiffTab(path);
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
              <span>{diffTab ? basename(originalPathFromDiffTab(path)) : basename(path)}</span>
              {diffTab && (
                <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[10px]">
                  DIFF
                </span>
              )}
              {isDirty && <span className="inline-block w-2 h-2 rounded-full bg-yellow-400" title="Unsaved changes" />}
            </span>

            {/* Save only applies to real files (not diff tabs). */}
            {isDirty && !diffTab && (
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

            {/* Apply/Discard controls for diff tabs */}
            {diffTab && (
              <>
                <button
                  className="p-1 rounded hover:bg-gray-800"
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (saving[path]) return;
                    const originalPath = originalPathFromDiffTab(path);
                    try {
                      setSaving((prev) => ({ ...prev, [path]: true }));
                      const content = state.draftContents[path] ?? state.fileContents[path] ?? '';

                      // Apply: write edited content to the real file.
                      await putFileContent(originalPath, content);
                      updateFileContent(originalPath, content);
                      markFileSaved(originalPath, content);

                      // Clear backend pending diff (so apply-all won't re-apply stale diffs)
                      try {
                        await approveDiff(originalPath, false);
                      } catch {
                        // ignore
                      }
                      removePendingDiff(originalPath);

                      // Refresh tree (new files may appear)
                      try {
                        const tree = await getFileTree();
                        updateFileTree(tree);
                      } catch {
                        // ignore
                      }

                      // Close the diff tab and switch to the real file.
                      closeFile(path);
                      openFile(originalPath);
                    } finally {
                      setSaving((prev) => ({ ...prev, [path]: false }));
                    }
                  }}
                  aria-label={`Apply ${basename(originalPathFromDiffTab(path))}`}
                  title="Apply"
                >
                  <Check size={14} className={saving[path] ? 'opacity-50' : ''} />
                </button>
                <button
                  className="p-1 rounded hover:bg-gray-800"
                  onClick={async (e) => {
                    e.stopPropagation();
                    const originalPath = originalPathFromDiffTab(path);
                    try {
                      await approveDiff(originalPath, false);
                    } catch {
                      // ignore
                    }
                    removePendingDiff(originalPath);
                    closeFile(path);
                  }}
                  aria-label={`Discard ${basename(originalPathFromDiffTab(path))}`}
                  title="Discard"
                >
                  <Trash2 size={14} />
                </button>
              </>
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

