'use client';

import React, { useState } from 'react';
import { useAgentStream } from "@/hooks/useAgentStream";
import { useProjectContext } from '@/context/ProjectContext';
import { downloadProject, applyAllDiffs, getFileTree, putFileContent } from '@/lib/api';
import { CheckCircle, XCircle, Loader2, Download, FileDiff } from 'lucide-react';

export default function AgentChat() {
  const [input, setInput] = useState("");
  const { startAgent, logs, isStreaming } = useAgentStream();
  const { state, clearPendingDiffs, setAuditResult, closeFile, updateFileTree } = useProjectContext();

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

  const handleApplyAll = async (approved: boolean) => {
    try {
      const diffFiles = Object.keys(state.pendingDiffs);
      const pendingCount = diffFiles.length;

      // Close all diff tabs in the editor
      for (const f of diffFiles) {
        closeFile(`__diff__/${f}`);
      }

      if (!approved) {
        await applyAllDiffs(false, state.activeRunId);
        clearPendingDiffs();
        return;
      }

      // Apply edited content if a diff tab exists/was edited; otherwise apply diff.newCode.
      for (const f of diffFiles) {
        const diff = state.pendingDiffs[f];
        const diffTabPath = `__diff__/${f}`;
        const edited = state.draftContents[diffTabPath] ?? state.fileContents[diffTabPath];
        const contentToWrite = edited ?? diff.newCode;
        await putFileContent(f, contentToWrite);
      }

      // Clear backend pending diffs (we applied ourselves).
      const result = await applyAllDiffs(false, state.activeRunId);
      clearPendingDiffs();

      // Refresh tree to reflect new/updated files.
      try {
        const tree = await getFileTree();
        updateFileTree(tree);
      } catch {
        // ignore
      }

      console.log(`✅ Applied ${result.applied} changes`);
    } catch (error) {
      console.error('Failed to apply all:', error);
    }
  };

  return (
    <>
      <div className="flex flex-col h-full">
        {/* Logs / Chat History */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {logs.length === 0 && !state.auditResult && (
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
                    className="flex-1 px-4 py-2 bg-green-500 hover:bg-green-400 text-white font-semibold rounded transition-colors"
                  >
                    Approve All
                  </button>
                  <button
                    onClick={() => handleApplyAll(false)}
                    className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-400 text-white font-semibold rounded transition-colors"
                  >
                    Discard All
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
        
          {logs.map((log, i) => (
            <div key={i} className="text-sm font-mono border-l-2 border-yellow-600 pl-2 py-1">
              {log}
            </div>
          ))}
        
          {isStreaming && (
            <div className="text-yellow-400 text-sm animate-pulse">
              Agent is thinking...
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-800 bg-gray-900">
          <form onSubmit={handleSubmit} className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the agent to refactor..."
              className="w-full bg-gray-800 text-white rounded p-3 text-sm focus:outline-none focus:ring-1 focus:ring-yellow-500 min-h-[80px]"
              disabled={isStreaming}
            />
            <button 
              type="submit" 
              disabled={isStreaming || !input.trim()}
              className="absolute bottom-3 right-3 bg-yellow-500 hover:bg-yellow-400 text-black px-3 py-1 rounded text-xs font-bold transition-colors disabled:opacity-50"
            >
              SEND
            </button>
          </form>
        </div>
      </div>

    </>
  );
}
