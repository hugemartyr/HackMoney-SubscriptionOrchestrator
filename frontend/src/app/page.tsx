'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import YellowEditor from '@/components/editor/YellowEditor';
import AgentChat from '@/components/chat/AgentChat';
import FileTree from '@/components/editor/FileTree';
import Terminal from '@/components/terminal/Terminal';
import ProjectUpload from '@/components/upload/ProjectUpload';
import { useProjectContext } from '@/context/ProjectContext';
import WorkspaceActionBar from '@/components/workspace/WorkspaceActionBar';
import { EnsProfile } from '@/components/EnsProfile';

const LAYOUT_STORAGE_KEY = 'workspace-layout-ratios';
// Allow full range so user can drag editor/chat and main/terminal as much as they want
const EDITOR_CHAT_MIN = 0.05;
const EDITOR_CHAT_MAX = 0.95;
const MAIN_TERMINAL_MIN = 0.05;
const MAIN_TERMINAL_MAX = 0.95;

function loadLayoutRatios(): { editorChat: number; mainTerminal: number } {
  if (typeof window === 'undefined') return { editorChat: 0.6, mainTerminal: 0.7 };
  try {
    const raw = localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as { editorChat?: number; mainTerminal?: number };
      return {
        editorChat: Math.max(EDITOR_CHAT_MIN, Math.min(EDITOR_CHAT_MAX, parsed.editorChat ?? 0.6)),
        mainTerminal: Math.max(MAIN_TERMINAL_MIN, Math.min(MAIN_TERMINAL_MAX, parsed.mainTerminal ?? 0.7)),
      };
    }
  } catch {
    // ignore
  }
  return { editorChat: 0.6, mainTerminal: 0.7 };
}

export default function WorkspacePage() {
  const { state } = useProjectContext();
  const [terminalMinimized, setTerminalMinimized] = useState(false);
  const [editorChatRatio, setEditorChatRatio] = useState(0.6);
  const [mainTerminalRatio, setMainTerminalRatio] = useState(0.7);
  const [isDraggingVertical, setIsDraggingVertical] = useState(false);
  const [isDraggingHorizontal, setIsDraggingHorizontal] = useState(false);
  const hasLoadedLayout = useRef(false);

  const topRegionRef = useRef<HTMLDivElement | null>(null);
  const splitContainerRef = useRef<HTMLDivElement | null>(null);
  const lastRatiosRef = useRef({ editorChat: editorChatRatio, mainTerminal: mainTerminalRatio });

  const clamp = (value: number, min: number, max: number) =>
    Math.min(max, Math.max(min, value));

  useEffect(() => {
    if (hasLoadedLayout.current) return;
    hasLoadedLayout.current = true;
    const { editorChat, mainTerminal } = loadLayoutRatios();
    setEditorChatRatio(editorChat);
    setMainTerminalRatio(mainTerminal);
    lastRatiosRef.current = { editorChat, mainTerminal };
  }, []);

  // Load project if ID is present in URL
  const searchParams = useSearchParams();
  const projectId = searchParams.get('projectId');
  const hasLoadedProject = useRef(false);

  useEffect(() => {
    if (!projectId || hasLoadedProject.current) return;

    const loadProject = async () => {
      try {
        hasLoadedProject.current = true;
        const res = await fetch(`http://localhost:8000/api/project/load/${projectId}`);
        if (!res.ok) throw new Error('Failed to load project');

        // Refresh file tree
        // This relies on the file tree component polling or us triggering a refresh
        // For now, we assume the file tree will pick up changes on next poll or we could reload page
        console.log('Project loaded successfully');
      } catch (error) {
        console.error('Error loading project:', error);
        alert('Failed to load project');
      }
    };

    loadProject();
  }, [projectId]);

  const handleWindowMouseMove = useCallback(
    (e: MouseEvent) => {
      if (isDraggingVertical && topRegionRef.current) {
        const rect = topRegionRef.current.getBoundingClientRect();
        const relativeX = e.clientX - rect.left;
        const ratio = clamp(relativeX / rect.width, EDITOR_CHAT_MIN, EDITOR_CHAT_MAX);
        setEditorChatRatio(ratio);
        lastRatiosRef.current = { ...lastRatiosRef.current, editorChat: ratio };
      }
      if (isDraggingHorizontal && splitContainerRef.current) {
        const rect = splitContainerRef.current.getBoundingClientRect();
        const relativeY = e.clientY - rect.top;
        const ratio = clamp(relativeY / rect.height, MAIN_TERMINAL_MIN, MAIN_TERMINAL_MAX);
        setMainTerminalRatio(ratio);
        lastRatiosRef.current = { ...lastRatiosRef.current, mainTerminal: ratio };
      }
    },
    [isDraggingVertical, isDraggingHorizontal]
  );

  const handleWindowMouseUp = useCallback(() => {
    if (isDraggingVertical) setIsDraggingVertical(false);
    if (isDraggingHorizontal) setIsDraggingHorizontal(false);
    try {
      const { editorChat, mainTerminal } = lastRatiosRef.current;
      localStorage.setItem(
        LAYOUT_STORAGE_KEY,
        JSON.stringify({ editorChat, mainTerminal })
      );
    } catch {
      // ignore
    }
  }, [isDraggingVertical, isDraggingHorizontal]);

  useEffect(() => {
    if (!isDraggingVertical && !isDraggingHorizontal) return;

    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', handleWindowMouseUp);
    // Prevent text selection while dragging
    document.body.style.userSelect = 'none';

    return () => {
      window.removeEventListener('mousemove', handleWindowMouseMove);
      window.removeEventListener('mouseup', handleWindowMouseUp);
      document.body.style.userSelect = '';
    };
  }, [isDraggingVertical, isDraggingHorizontal, handleWindowMouseMove, handleWindowMouseUp]);

  // Show upload page if project not uploaded
  if (!state.isUploaded) {
    return <ProjectUpload />;
  }

  // Show workspace if project is uploaded
  return (
    <div className="flex h-screen bg-black text-white overflow-hidden">
      {/* Sidebar - File Explorer */}
      <aside className="w-64 border-r border-gray-800 hidden md:block">
        <FileTree />
      </aside>

      {/* Main Content - Split View */}
      <main className="flex-1 flex flex-col">
        {/* Top Header */}
        <header className="h-12 border-b border-gray-800 bg-black flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded bg-yellow-500 flex items-center justify-center text-black font-bold text-xs ring-1 ring-white/20">
              Y
            </div>
            <h1 className="text-sm font-bold tracking-tight text-gray-200">
              {projectId ? `Project: ${projectId.slice(0, 8)}` : 'Yellow Agent Factory'}
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <EnsProfile />
          </div>
        </header>

        <div
          ref={splitContainerRef}
          className="flex-1 flex flex-col min-h-0"
        >
          {/* Top: Editor + Chat + Action Bar */}
          <div
            ref={topRegionRef}
            className="flex flex-col min-h-0"
            style={{
              flexBasis: terminalMinimized ? 'calc(100% - 40px)' : `${mainTerminalRatio * 100}%`,
              flexGrow: 0,
              flexShrink: 0,
            }}
          >
            {/* Editor and Chat */}
            <div className="flex-1 flex flex-col md:flex-row min-h-0">
              {/* Left: Code Editor */}
              <div
                className="border-r border-gray-800 min-h-0 min-w-0 flex flex-col"
                style={{
                  flexBasis: `${editorChatRatio * 100}%`,
                  flexGrow: 0,
                  flexShrink: 0,
                }}
              >
                <YellowEditor />
              </div>

              {/* Vertical Splitter */}
              <div
                role="separator"
                aria-orientation="vertical"
                aria-label="Resize editor and agent chat"
                className="hidden md:block w-1 cursor-col-resize bg-gray-800/70 hover:bg-yellow-500/70 transition-colors"
                onMouseDown={(e) => {
                  e.preventDefault();
                  setIsDraggingVertical(true);
                }}
              />

              {/* Right: Agent Interface */}
              <div
                className="flex flex-col bg-gray-900 border-r border-gray-800 min-h-0 min-w-0"
                style={{
                  flexBasis: `${(1 - editorChatRatio) * 100}%`,
                  flexGrow: 1,
                  flexShrink: 1,
                }}
              >
                <AgentChat />
              </div>
            </div>

            {/* Action Bar */}
            <WorkspaceActionBar
              terminalMinimized={terminalMinimized}
              onToggleTerminal={() => setTerminalMinimized(v => !v)}
            />
          </div>

          {/* Horizontal Splitter */}
          {!terminalMinimized && (
            <div
              role="separator"
              aria-orientation="horizontal"
              aria-label="Resize workspace and terminal"
              className="h-1 cursor-row-resize bg-gray-800/70 hover:bg-yellow-500/70 transition-colors"
              onMouseDown={(e) => {
                e.preventDefault();
                setIsDraggingHorizontal(true);
              }}
            />
          )}

          {/* Bottom: Terminal */}
          <div
            className="border-t border-gray-800 bg-black min-h-0"
            style={{
              flexBasis: terminalMinimized ? '40px' : `${(1 - mainTerminalRatio) * 100}%`,
              flexGrow: 0,
              flexShrink: 0,
            }}
          >
            <Terminal />
          </div>
        </div>
      </main>
    </div>
  );
}
