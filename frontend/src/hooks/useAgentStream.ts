import { useRef, useState } from 'react';
import { SSEEvent } from '@/lib/types';
import { useProjectContext } from '@/context/ProjectContext';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
import { resumeAgentFetch } from '@/lib/api';

export function useAgentStream() {
  const [logs, setLogs] = useState<string[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const runIdRef = useRef(0);
  const {
    updateFileTree,
    updateFileContent,
    addTerminalLog,
    setAuditResult,
    addPendingDiff,
    state,
    setBuildStatus,
    openFile,
    setActiveRunId,
    setApprovalPending,
    setApprovalFiles,
  } = useProjectContext();

  const startAgent = async (prompt: string) => {
    // Prevent double-submit/races that can create multiple concurrent streams.
    if (isStreaming) return;

    setIsStreaming(true);
    // Prepend user message so chat shows "You" vs "Agent" correctly
    setLogs([`USER: ${prompt}`]);

    try {
      // Abort any previous stream (best-effort).
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      const runId = ++runIdRef.current;

      const response = await fetch(`${API_BASE_URL}/api/yellow-agent/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Agent stream failed: ${response.status}`);
      }
      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        // If a new run starts, stop processing this one.
        if (runId !== runIdRef.current) break;
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
      // Ignore aborts (expected when restarting).
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      setLogs(prev => [...prev, `❌ Error connecting to agent`]);
      console.error(err);
    } finally {
      setIsStreaming(false);
    }
  };

  const consumeResumeStream = async (response: Response) => {
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
            console.error('Stream parse error', e);
          }
        }
      }
    }
  };

  const resumeAgent = async (runId: string, approved: boolean) => {
    if (isStreaming) return;
    if (!runId) {
      console.warn('resumeAgent: no runId');
      return;
    }
    setIsStreaming(true);
    try {
      const response = await resumeAgentFetch(runId, approved);
      if (!response.ok) {
        throw new Error(`Resume failed: ${response.status}`);
      }
      await consumeResumeStream(response);
    } catch (err) {
      setLogs(prev => [...prev, `❌ Error resuming agent`]);
      console.error(err);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleEvent = (event: SSEEvent) => {
    // Run scoping: only process events for the active run.
    if (event.type === 'run_started') {
      setActiveRunId(event.runId);
    } else if ('runId' in event && typeof (event as any).runId === 'string') {
      const runId = (event as any).runId as string;
      if (state.activeRunId && runId !== state.activeRunId) return;
    }

    switch (event.type) {
      case 'run_started':
        setLogs(prev => [...prev, `▶️ Run started (${event.runId})`]);
        break;

      case 'run_finished': {
        const ev = event as { runId: string; interrupted?: boolean };
        setLogs(prev => [...prev, `⏹️ Run finished (${ev.runId})`]);
        if (!ev.interrupted) {
          setActiveRunId(null);
        }
        break;
      }

      case 'thought':
        setLogs(prev => [...prev, `🤖 ${event.content}`]);
        break;

      case 'tool_start':
        setLogs(prev => [...prev, `🛠️ Running: ${event.name}...`]);
        break;

      case 'tool_end':
        // Keep logs cleaner; optional to log completion.
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
        if (event.runId) setActiveRunId(event.runId);
        addPendingDiff({
          file: event.file,
          oldCode: event.oldCode,
          newCode: event.newCode,
        });
        // Open proposed changes as a virtual editor tab.
        // We store the proposed new code under a virtual path so the editor can treat it like a normal file.
        const diffTabPath = `__diff__/${event.file}`;
        updateFileContent(diffTabPath, event.newCode);
        openFile(diffTabPath);
        const pendingCount = Object.keys(state.pendingDiffs).length + 1;
        setLogs(prev => [...prev, `📋 Diff ready for: ${event.file} (${pendingCount} pending)`]);
        break;

      case 'proposed_file': {
        if (event.runId) setActiveRunId(event.runId);
        // Preferred event for editor proposals
        const diffTabPath = `__diff__/${event.path}`;
        updateFileContent(diffTabPath, event.content);
        openFile(diffTabPath);
        setLogs(prev => [...prev, `📋 Proposed file ready: ${event.path}`]);
        break;
      }

      case 'awaiting_user_review':
        setLogs(prev => [...prev, `🧾 Awaiting review (${event.files.length} files)`]);
        setApprovalPending(true);
        setApprovalFiles(event.files);
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

  /** Consume an SSE resume/apply stream (e.g. from apply endpoint) and update streaming state. */
  const resumeFromStream = async (response: Response) => {
    if (isStreaming) return;
    setIsStreaming(true);
    try {
      if (!response.ok) throw new Error(`Stream failed: ${response.status}`);
      await consumeResumeStream(response);
    } catch (err) {
      setLogs(prev => [...prev, `❌ Error resuming agent`]);
      console.error(err);
    } finally {
      setIsStreaming(false);
    }
  };

  return { startAgent, resumeAgent, consumeResumeStream, resumeFromStream, logs, isStreaming, setLogs };
}
