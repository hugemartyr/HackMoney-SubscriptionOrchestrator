import { useState } from 'react';
import { SSEEvent } from '@/lib/types';
import { useProjectContext } from '@/context/ProjectContext';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useAgentStream() {
  const [logs, setLogs] = useState<string[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const {
    updateFileTree,
    updateFileContent,
    addTerminalLog,
    setAuditResult,
    addPendingDiff,
    state,
    setBuildStatus,
  } = useProjectContext();

  const startAgent = async (prompt: string) => {
    setIsStreaming(true);
    setLogs([]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/yellow-agent/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: SSEEvent = JSON.parse(line.replace('data: ', ''));
              handleEvent(data);
            } catch (e) {
              console.error("Stream parse error", e);
            }
          }
        }
      }
    } catch (err) {
      setLogs(prev => [...prev, `❌ Error connecting to agent`]);
      console.error(err);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleEvent = (event: SSEEvent) => {
    switch (event.type) {
      case 'thought':
        setLogs(prev => [...prev, `🤖 ${event.content}`]);
        break;

      case 'tool':
        setLogs(prev => [...prev, `🛠️ Running: ${event.name}...`]);
        break;

      case 'file_tree':
        updateFileTree(event.tree);
        setLogs(prev => [...prev, `📁 File tree updated`]);
        break;

      case 'file_content':
        updateFileContent(event.path, event.content);
        setLogs(prev => [...prev, `📝 Updated: ${event.path}`]);
        break;

      case 'terminal':
        addTerminalLog(event.line);
        break;

      case 'audit':
        setAuditResult(event.analysis);
        setLogs(prev => [...prev, `🔍 Audit complete: ${event.analysis.framework} detected`]);
        break;

      case 'diff':
        addPendingDiff({
          file: event.file,
          oldCode: event.oldCode,
          newCode: event.newCode,
        });
        const pendingCount = Object.keys(state.pendingDiffs).length + 1;
        setLogs(prev => [...prev, `📋 Diff ready for: ${event.file} (${pendingCount} pending)`]);
        break;

      case 'build':
        if (event.status === 'start') {
          setBuildStatus('building');
          setLogs(prev => [...prev, `🔨 Build started...`]);
        } else if (event.status === 'output') {
          if (event.data) {
            addTerminalLog(event.data);
          }
        } else if (event.status === 'success') {
          setBuildStatus('success', event.data || '');
          setLogs(prev => [...prev, `✅ Build successful!`]);
        } else if (event.status === 'error') {
          setBuildStatus('error', event.data || '');
          setLogs(prev => [...prev, `❌ Build failed: ${event.data || 'Unknown error'}`]);
        }
        break;

      case 'code_update':
        // Legacy support - treat as file_content for current file
        setLogs(prev => [...prev, `✅ Code Updated!`]);
        break;

      default:
        console.warn('Unknown event type:', event);
    }
  };

  return { startAgent, logs, isStreaming };
}
