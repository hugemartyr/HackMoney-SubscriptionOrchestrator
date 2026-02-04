'use client';

import React, { useEffect, useRef } from 'react';
import { useProjectContext } from '@/context/ProjectContext';

export default function Terminal() {
  const { state } = useProjectContext();
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new logs arrive
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [state.terminalLogs]);

  return (
    <div className="h-full flex flex-col bg-gray-950 border-t border-gray-800">
      <div className="px-4 py-2 bg-gray-900 border-b border-gray-800">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Terminal
        </h3>
      </div>
      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm text-green-400"
        style={{ backgroundColor: '#0a0a0a' }}
      >
        {state.terminalLogs.length === 0 ? (
          <div className="text-gray-600">No output yet...</div>
        ) : (
          state.terminalLogs.map((line, index) => (
            <div key={index} className="mb-1">
              {line.startsWith('>') ? (
                <span className="text-yellow-400">{line}</span>
              ) : (
                <span>{line}</span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
