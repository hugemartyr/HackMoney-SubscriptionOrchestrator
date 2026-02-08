'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useProjectContext } from '@/context/ProjectContext';
import { runTerminalCommand } from '@/lib/api';

export default function Terminal() {
  const { state, addTerminalLog } = useProjectContext();
  const terminalRef = useRef<HTMLDivElement>(null);
  const [command, setCommand] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    // Auto-scroll to bottom when new logs arrive
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [state.terminalLogs]);

  // Group logs by commands (lines starting with ">")
  const groupedLogs = React.useMemo(() => {
    const groups: { command: string | null; lines: string[] }[] = [];
    let current: { command: string | null; lines: string[] } | null = null;

    state.terminalLogs.forEach((line) => {
      if (line.startsWith('>')) {
        // start new group
        if (current) {
          groups.push(current);
        }
        current = { command: line, lines: [] };
      } else {
        if (!current) {
          current = { command: null, lines: [] };
        }
        current.lines.push(line);
      }
    });

    if (current) {
      groups.push(current);
    }

    return groups;
  }, [state.terminalLogs]);

  const handleKeyDown = async (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter' || isRunning) return;

    const trimmed = command.trim();
    if (!trimmed) return;

    event.preventDefault();

    // Echo the command in the terminal with a leading ">" so it gets highlighted.
    addTerminalLog(`> ${trimmed}`);
    setCommand('');
    setIsRunning(true);

    try {
      const result = await runTerminalCommand(trimmed);

      result.stdout.forEach(line => {
        if (line) addTerminalLog(line);
      });

      result.stderr.forEach(line => {
        if (line) addTerminalLog(line);
      });

      addTerminalLog(`[exit ${result.exitCode}]`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to run terminal command';
      addTerminalLog(`! ${message}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-950 border-t border-gray-800 relative">
      <div className="px-4 py-2 bg-gray-900 border-b border-gray-800 shrink-0">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Terminal
        </h3>
      </div>
      {/* Scrollable output only; input overlays at bottom */}
      <div
        ref={terminalRef}
        className="flex-1 min-h-0 overflow-y-auto p-3 pb-14 font-mono text-xs sm:text-sm text-green-400 space-y-2"
        style={{ backgroundColor: '#050505' }}
      >
        {state.terminalLogs.length === 0 ? (
          <div className="text-gray-600">No output yet...</div>
        ) : (
          <div className="space-y-2">
            {groupedLogs.map((group, groupIndex) => (
              <div
                key={groupIndex}
                className="rounded-md border border-gray-800 bg-black/70 overflow-hidden"
              >
                {group.command && (
                  <div className="px-3 py-1.5 bg-gray-900/90 border-b border-gray-800 flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-[0.18em] text-gray-500">
                      Command
                    </span>
                    <span className="text-yellow-300 text-xs">
                      {group.command.replace(/^>\s?/, '> ')}
                    </span>
                  </div>
                )}
                <div className="px-3 py-2 space-y-1">
                  {group.lines.length === 0 && group.command && (
                    <div className="text-gray-700 text-[11px] italic">
                      (no output)
                    </div>
                  )}
                  {group.lines.map((line, index) => {
                    const trimmed = line.trim();
                    const isExit = /^\[exit\s+\d+]/.test(trimmed);
                    const isError =
                      trimmed.startsWith('!') ||
                      /error|failed|exception/i.test(trimmed);

                    const lineClass = isExit
                      ? 'text-gray-500'
                      : isError
                        ? 'text-red-400'
                        : 'text-green-400';

                    return (
                      <div
                        key={index}
                        className={`text-[11px] sm:text-xs leading-relaxed break-all overflow-hidden ${lineClass}`}
                      >
                        {trimmed}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      {/* Input fixed at bottom so it stays visible and doesn't push down */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-gray-800 px-3 py-2 bg-gray-950/95 backdrop-blur-sm">
        <input
          type="text"
          className="w-full bg-black text-green-400 font-mono text-sm px-2 py-1 rounded border border-gray-700 outline-none focus:border-yellow-500 disabled:opacity-60"
          placeholder={
            state.isUploaded
              ? isRunning
                ? 'Running command...'
                : 'Enter a command and press Enter'
              : 'Upload a project before running terminal commands'
          }
          value={command}
          onChange={event => setCommand(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!state.isUploaded || isRunning}
        />
      </div>
    </div>
  );
}
