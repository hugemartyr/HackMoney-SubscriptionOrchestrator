'use client';

import React from 'react';
import { X, Check, XCircle } from 'lucide-react';
import { DiffData } from '@/lib/types';
import { approveDiff } from '@/lib/api';

interface DiffViewProps {
  diff: DiffData;
  onClose: () => void;
  onApproved: () => void;
}

export default function DiffView({ diff, onClose, onApproved }: DiffViewProps) {
  const handleApprove = async () => {
    try {
      await approveDiff(diff.file, true);
      onApproved();
      onClose();
    } catch (error) {
      console.error('Failed to approve diff:', error);
    }
  };

  const handleReject = async () => {
    try {
      await approveDiff(diff.file, false);
      onClose();
    } catch (error) {
      console.error('Failed to reject diff:', error);
    }
  };

  // Simple diff view - split old vs new
  const oldLines = diff.oldCode.split('\n');
  const newLines = diff.newCode.split('\n');

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-lg w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Review Changes</h2>
            <p className="text-sm text-gray-400 mt-1">{diff.file}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded transition-colors"
          >
            <X size={20} className="text-gray-400" />
          </button>
        </div>

        {/* Diff Content */}
        <div className="flex-1 overflow-auto flex">
          {/* Old Code */}
          <div className="flex-1 border-r border-gray-800">
            <div className="sticky top-0 bg-red-900/20 px-4 py-2 border-b border-gray-800">
              <span className="text-sm font-semibold text-red-400">Old Code</span>
            </div>
            <div className="p-4 font-mono text-sm">
              <pre className="text-gray-400 whitespace-pre-wrap">
                {diff.oldCode || '(empty)'}
              </pre>
            </div>
          </div>

          {/* New Code */}
          <div className="flex-1">
            <div className="sticky top-0 bg-green-900/20 px-4 py-2 border-b border-gray-800">
              <span className="text-sm font-semibold text-green-400">New Code</span>
            </div>
            <div className="p-4 font-mono text-sm">
              <pre className="text-gray-300 whitespace-pre-wrap">
                {diff.newCode || '(empty)'}
              </pre>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t border-gray-800 flex items-center justify-end gap-3">
          <button
            onClick={handleReject}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded flex items-center gap-2 transition-colors"
          >
            <XCircle size={16} />
            Reject
          </button>
          <button
            onClick={handleApprove}
            className="px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded flex items-center gap-2 transition-colors"
          >
            <Check size={16} />
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
