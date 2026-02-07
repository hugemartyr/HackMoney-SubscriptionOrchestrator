'use client';

import React, { useMemo, useState } from 'react';
import { useAgentStream } from "@/hooks/useAgentStream";
import { useProjectContext } from '@/context/ProjectContext';
import { downloadProject, applyAllDiffs, getFileTree, putFileContent } from '@/lib/api';
import {
  CheckCircle,
  XCircle,
  Loader2,
  Download,
  FileDiff,
  AlertCircle,
  Bot,
  User,
} from 'lucide-react';

export default function AgentChat() {
  const [input, setInput] = useState("");
  const [isApplying, setIsApplying] = useState(false);
  const { startAgent, resumeAgent, resumeFromStream, logs, isStreaming } = useAgentStream();
  const {
    state,
    clearPendingDiffs,
    setAuditResult,
    closeFile,
    updateFileTree,
    setApprovalPending,
    setApprovalFiles,
  } = useProjectContext();

  /**
   * Classify log lines to match backend stream format from useAgentStream:
   * - USER: … (prepended when user sends a message) → user bubble
   * - 🤖 … (thought events) → agent message bubble
   * - ▶️ ⏹️ 🛠️ 📁 📝 🔍 📋 🧾 🔨 ✅ ❌ → system-style compact lines
   * - AGENT: / SYSTEM: kept for future backend use
   */
  const parsedMessages = useMemo(() => {
    const agentEmoji = /^🤖\s*/;
    const systemEmoji = /^(▶️|⏹️|🛠️|📁|📝|🔍|📋|🧾|🔨|✅|❌)/;
    return logs.map((raw) => {
      const trimmed = raw.trim();
      if (trimmed.startsWith('USER:')) {
        return { role: 'user' as const, text: trimmed.replace(/^USER:\s*/i, '').trim() };
      }
      if (trimmed.startsWith('AGENT:')) {
        return { role: 'agent' as const, text: trimmed.replace(/^AGENT:\s*/i, '').trim() };
      }
      if (trimmed.startsWith('SYSTEM:')) {
        return { role: 'system' as const, text: trimmed.replace(/^SYSTEM:\s*/i, '').trim() };
      }
      if (agentEmoji.test(trimmed)) {
        return { role: 'agent' as const, text: trimmed.replace(agentEmoji, '').trim() };
      }
      if (systemEmoji.test(trimmed)) {
        return { role: 'system' as const, text: trimmed };
      }
      return { role: 'log' as const, text: raw };
    });
  }, [logs]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isStreaming) return;
    if (!input.trim()) return;
    
    startAgent(input);
    setInput("");
  };

  const handleProceed = () => {
    setAuditResult(null);
    // Agent will continue automatically after audit approval
  };

  const handleCancel = () => {
    setAuditResult(null);
  };

  const handleDownload = async () => {
    try {
      const blob = await downloadProject();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${state.projectName || 'project'}-yellow-fied.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const handleApproveAll = async () => {
    try {
      if (!state.activeRunId) return;
      setApprovalPending(false);
      setApprovalFiles([]);
      // Close diff tabs
      for (const f of state.approvalFiles) {
        closeFile(`__diff__/${f}`);
      }
      clearPendingDiffs();
      await resumeAgent(state.activeRunId, true);
    } catch (error) {
      console.error('Failed to approve files:', error);
    }
  };

  const handleRejectAll = async () => {
    try {
      if (!state.activeRunId) return;
      setApprovalPending(false);
      setApprovalFiles([]);
      for (const f of state.approvalFiles) {
        closeFile(`__diff__/${f}`);
      }
      clearPendingDiffs();
      await resumeAgent(state.activeRunId, false);
    } catch (error) {
      console.error('Failed to reject files:', error);
    }
  };

  const handleApplyAll = async (approved: boolean) => {
    const runId = state.activeRunId;
    const diffFiles = Object.keys(state.pendingDiffs);
    if (diffFiles.length === 0) return;

    try {
      setIsApplying(true);
      // Close all diff tabs in the editor
      for (const f of diffFiles) {
        closeFile(`__diff__/${f}`);
      }
      setApprovalPending(false);
      setApprovalFiles([]);

      if (!approved) {
        // Discard All: clear local state, backend discards and streams resume (uses runId or last run)
        clearPendingDiffs();
        const result = await applyAllDiffs(false, runId ?? null, true);
        if (result instanceof Response) {
          await resumeFromStream(result);
        }
        return;
      }

      // Approve All: write (possibly edited) content to backend files, clear backend diffs, then resume workflow
      for (const f of diffFiles) {
        const diff = state.pendingDiffs[f];
        const diffTabPath = `__diff__/${f}`;
        const edited = state.draftContents[diffTabPath] ?? state.fileContents[diffTabPath];
        const contentToWrite = edited ?? diff.newCode;
        await putFileContent(f, contentToWrite);
      }
      clearPendingDiffs();

      // Clear backend pending diffs (no resume), then resume workflow so backend does not overwrite our written content
      await applyAllDiffs(false, runId ?? null, false);
      if (runId) {
        await resumeAgent(runId, true);
      }

      try {
        const tree = await getFileTree();
        updateFileTree(tree);
      } catch {
        // ignore
      }
    } catch (error) {
      console.error('Failed to apply all:', error);
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <>
      <div className="flex flex-col h-full bg-gradient-to-b from-gray-950 via-gray-900 to-black">
        {/* Planning / Agent State Header */}
        <div className="border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-sm px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-yellow-500/10 border border-yellow-500/50 flex items-center justify-center">
                <Bot className="h-4 w-4 text-yellow-400" />
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.18em] text-gray-500">
                  Yellow Agent
                </div>
                <div className="text-sm font-semibold text-gray-100">
                  {isStreaming ? 'Thinking through a plan...' : 'Ready for your next task'}
                </div>
              </div>
            </div>
            {isStreaming && (
              <div className="flex items-center gap-2 text-xs text-yellow-300">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500" />
                </span>
                <span>Agent is thinking</span>
              </div>
            )}
          </div>

          {/* Simple planning nodes with animated connecting lines */}
          <div className="mt-3 rounded-lg bg-gray-900/70 border border-gray-800/80 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              {['Understand', 'Plan', 'Edit', 'Verify'].map((label, index) => {
                const activeIndex = isStreaming ? 1 : 3;
                const isActive = index === activeIndex;
                return (
                  <div key={label} className="flex-1 flex items-center gap-2">
                    <div
                      className={[
                        'flex-1 rounded-md px-2 py-1.5 text-[10px] text-center uppercase tracking-wide',
                        'transition-all duration-300',
                        isActive
                          ? 'bg-yellow-500/20 border border-yellow-400/70 text-yellow-200 shadow-[0_0_18px_rgba(234,179,8,0.35)]'
                          : 'bg-gray-900/80 border border-gray-700/70 text-gray-400',
                      ].join(' ')}
                    >
                      {label}
                    </div>
                    {index < 3 && (
                      <div className="w-6 h-px relative overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-r from-gray-700 via-yellow-500 to-gray-700 opacity-50" />
                        {isStreaming && (
                          <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(250,204,21,0.9),transparent)] animate-[slide-line_1200ms_linear_infinite]" />
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Logs / Chat History */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {logs.length === 0 && !state.auditResult && !state.approvalPending && (
            <div className="text-gray-500 text-center mt-10">
              <h3 className="text-lg font-bold text-yellow-500">Yellow Agent</h3>
              <p className="text-sm">Ready to integrate State Channels.</p>
            </div>
          )}

          {/* Audit Card */}
          {state.auditResult && (
            <div className="bg-yellow-500/10 border border-yellow-500/50 rounded-lg p-4 mb-4">
              <h3 className="text-lg font-semibold text-yellow-400 mb-3">Audit Complete</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-gray-400">Framework: </span>
                  <span className="text-white font-semibold">{state.auditResult.framework}</span>
                </div>
                <div>
                  <span className="text-gray-400">Current Payment: </span>
                  <span className="text-white">{state.auditResult.currentPayment}</span>
                </div>
                <div>
                  <span className="text-gray-400">Fee Savings: </span>
                  <span className="text-green-400 font-semibold">{state.auditResult.feeSavings}</span>
                </div>
                <div className="mt-3">
                  <span className="text-gray-400 block mb-2">Proposed Changes:</span>
                  <ul className="list-disc list-inside space-y-1 text-gray-300">
                    {state.auditResult.proposedChanges.map((change, i) => (
                      <li key={i}>{change}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button
                  onClick={handleProceed}
                  className="flex-1 px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded transition-colors"
                >
                  Proceed
                </button>
                <button
                  onClick={handleCancel}
                  className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Approval Required Card */}
          {state.approvalPending && state.approvalFiles.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/50 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle size={16} className="text-yellow-400" />
                <span className="text-yellow-400 font-semibold">
                  Approval Required ({state.approvalFiles.length} files)
                </span>
              </div>
              <p className="text-sm text-gray-300 mb-3">
                The agent is waiting for your approval to proceed with these changes:
              </p>
              <ul className="list-disc list-inside text-sm text-gray-400 mb-3 space-y-1">
                {state.approvalFiles.map((file, idx) => (
                  <li key={idx}>{file}</li>
                ))}
              </ul>
              <div className="flex gap-2 mt-4">
                <button
                  onClick={handleApproveAll}
                  className="flex-1 px-4 py-2 bg-green-500 hover:bg-green-400 text-white font-semibold rounded transition-colors"
                >
                  Approve & Continue
                </button>
                <button
                  onClick={handleRejectAll}
                  className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-400 text-white font-semibold rounded transition-colors"
                >
                  Reject & Stop
                </button>
              </div>
            </div>
          )}



          {/* Build Status */}
          {state.buildStatus !== 'idle' && (
            <div className={`rounded-lg p-4 mb-4 ${
              state.buildStatus === 'success' 
                ? 'bg-green-500/10 border border-green-500/50' 
                : state.buildStatus === 'error'
                ? 'bg-red-500/10 border border-red-500/50'
                : 'bg-yellow-500/10 border border-yellow-500/50'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {state.buildStatus === 'building' && (
                  <Loader2 size={16} className="text-yellow-400 animate-spin" />
                )}
                {state.buildStatus === 'success' && (
                  <CheckCircle size={16} className="text-green-400" />
                )}
                {state.buildStatus === 'error' && (
                  <XCircle size={16} className="text-red-400" />
                )}
                <span className={`font-semibold ${
                  state.buildStatus === 'success' 
                    ? 'text-green-400' 
                    : state.buildStatus === 'error'
                    ? 'text-red-400'
                    : 'text-yellow-400'
                }`}>
                  {state.buildStatus === 'building' && 'Building...'}
                  {state.buildStatus === 'success' && 'Build Successful!'}
                  {state.buildStatus === 'error' && 'Build Failed'}
                </span>
              </div>
              {state.buildOutput && (
                <pre className="text-xs font-mono text-gray-300 mt-2 whitespace-pre-wrap">
                  {state.buildOutput}
                </pre>
              )}
              {state.buildStatus === 'success' && (
                <button
                  onClick={handleDownload}
                  className="mt-3 w-full px-4 py-2 bg-green-500 hover:bg-green-400 text-white font-semibold rounded flex items-center justify-center gap-2 transition-colors"
                >
                  <Download size={16} />
                  Download Yellow-fied Project
                </button>
              )}
            </div>
          )}
          {/* Conversation + logs */}
          {parsedMessages.length > 0 && (
            <div className="space-y-2">
              {parsedMessages.map((msg, i) => {
                if (msg.role === 'user') {
                  return (
                    <div key={i} className="flex justify-end">
                      <div className="max-w-[80%] flex items-end gap-2">
                        <div className="rounded-2xl rounded-br-sm bg-yellow-500 text-black px-3 py-2 text-xs sm:text-sm shadow-lg shadow-yellow-500/20 transition-all duration-300">
                          {msg.text}
                        </div>
                        <div className="h-7 w-7 rounded-full bg-yellow-400 flex items-center justify-center shadow-md shadow-yellow-500/30">
                          <User className="h-3 w-3 text-black" />
                        </div>
                      </div>
                    </div>
                  );
                }

                if (msg.role === 'agent') {
                  return (
                    <div key={i} className="flex justify-start">
                      <div className="max-w-[80%] flex items-end gap-2">
                        <div className="h-7 w-7 rounded-full bg-gray-900 border border-yellow-500/60 flex items-center justify-center shadow-md shadow-yellow-500/30">
                          <Bot className="h-3 w-3 text-yellow-300" />
                        </div>
                        <div className="rounded-2xl rounded-bl-sm bg-gray-900/90 border border-gray-700 px-3 py-2 text-xs sm:text-sm text-gray-100 shadow-lg shadow-black/40 transition-all duration-300">
                          {msg.text}
                        </div>
                      </div>
                    </div>
                  );
                }

                if (msg.role === 'system') {
                  return (
                    <div
                      key={i}
                      className="text-[11px] sm:text-xs font-mono text-gray-400 bg-gray-900/60 border border-gray-800 rounded px-2 py-1"
                    >
                      {msg.text}
                    </div>
                  );
                }

                // raw log line
                return (
                  <div
                    key={i}
                    className="text-[11px] sm:text-xs font-mono border-l-2 border-yellow-600/60 pl-2 py-1 text-gray-200 bg-gray-950/60"
                  >
                    {msg.text}
                  </div>
                );
              })}
            </div>
          )}

          {isStreaming && (
            <div className="mt-3 flex items-center gap-2 text-xs text-yellow-300">
              <div className="flex gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-bounce [animation-delay:-0.2s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-bounce [animation-delay:-0.05s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-bounce [animation-delay:0.1s]" />
              </div>
              <span>Composing a response…</span>
            </div>
          )}
        </div>

       {/* Pending Diffs Summary */}
                  {Object.keys(state.pendingDiffs).length > 0 && (
            <div className="bg-blue-500/10 border border-blue-500/50 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-2 mb-3">
                <FileDiff size={16} className="text-blue-400" />
                <span className="text-blue-400 font-semibold">
                  Changes Ready for Review ({Object.keys(state.pendingDiffs).length})
                </span>
              </div>
              <p className="text-sm text-gray-300 mb-3">
                Diffs are opened as editor tabs. Review and edit them, then apply from the tab or use Apply/Discard All.
              </p>
                <div className="flex gap-2 pt-2 border-t border-gray-700">
                  <button
                    onClick={() => handleApplyAll(true)}
                    disabled={isApplying || isStreaming}
                    className="flex-1 px-4 py-2 bg-green-500 hover:bg-green-400 text-white font-semibold rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isApplying ? 'Applying…' : 'Approve All'}
                  </button>
                  <button
                    onClick={() => handleApplyAll(false)}
                    disabled={isApplying || isStreaming}
                    className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-400 text-white font-semibold rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Discard All
                  </button>
                </div>
            </div>
          )}


        {/* Input Area */}
        <div className="p-4 border-t border-gray-800 bg-gray-950/95 backdrop-blur">
          <form onSubmit={handleSubmit} className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the agent to audit, refactor, or add a feature…"
              className="w-full bg-gray-900 text-white rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-yellow-500 min-h-[80px] border border-gray-800/80 pr-20"
              disabled={isStreaming}
            />
            <button 
              type="submit" 
              disabled={isStreaming || !input.trim()}
              className="absolute bottom-3 right-3 bg-yellow-500 hover:bg-yellow-400 text-black px-3 py-1.5 rounded-md text-xs font-bold transition-colors disabled:opacity-50 shadow-md shadow-yellow-500/40"
            >
              SEND
            </button>
          </form>
        </div>
      </div>

    </>
  );
}
