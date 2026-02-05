'use client';

import React from 'react';

type Props = {
  terminalMinimized: boolean;
  onToggleTerminal: () => void;
};

export default function WorkspaceActionBar({ terminalMinimized, onToggleTerminal }: Props) {
  return (
    <div className="h-10 flex items-center justify-between px-3 bg-gray-950 border-t border-gray-800">
      <button
        onClick={onToggleTerminal}
        className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded"
      >
        {terminalMinimized ? 'Show Terminal' : 'Minimize Terminal'}
      </button>

      <div className="flex items-center gap-2">
        <button
          disabled
          className="px-3 py-1 text-xs bg-yellow-500 text-black font-semibold rounded opacity-50 cursor-not-allowed"
          title="Coming soon"
        >
          Save
        </button>
        <button
          disabled
          className="px-3 py-1 text-xs bg-gray-800 rounded opacity-50 cursor-not-allowed"
          title="Coming soon"
        >
          Dev
        </button>
        <button
          disabled
          className="px-3 py-1 text-xs bg-gray-800 rounded opacity-50 cursor-not-allowed"
          title="Coming soon"
        >
          Build
        </button>
      </div>
    </div>
  );
}

