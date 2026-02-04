'use client';

import React, { useState } from 'react';
import YellowEditor from '@/components/editor/YellowEditor';
import AgentChat from '@/components/chat/AgentChat';
import FileTree from '@/components/editor/FileTree';
import Terminal from '@/components/terminal/Terminal';
import ProjectUpload from '@/components/upload/ProjectUpload';
import { useProjectContext } from '@/context/ProjectContext';
import WorkspaceActionBar from '@/components/workspace/WorkspaceActionBar';

export default function WorkspacePage() {
  const { state } = useProjectContext();
  const [terminalMinimized, setTerminalMinimized] = useState(false);

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
        {/* Top: Editor and Chat */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0">
          {/* Left: Code Editor */}
          <div className="flex-1 border-r border-gray-800 min-h-0">
            <YellowEditor />
          </div>

          {/* Right: Agent Interface */}
          <div className="w-full md:w-[400px] lg:w-[500px] flex flex-col bg-gray-900 border-r border-gray-800">
            <AgentChat />
          </div>
        </div>

        {/* Action Bar */}
        <WorkspaceActionBar
          terminalMinimized={terminalMinimized}
          onToggleTerminal={() => setTerminalMinimized(v => !v)}
        />

        {/* Bottom: Terminal */}
        <div className={(terminalMinimized ? 'h-10' : 'h-64') + ' border-t border-gray-800'}>
          <Terminal />
        </div>
      </main>
    </div>
  );
}
