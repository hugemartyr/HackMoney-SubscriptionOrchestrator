'use client';

import React, { useState } from 'react';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useRouter } from 'next/navigation';

type Props = {
  terminalMinimized: boolean;
  onToggleTerminal: () => void;
};

export default function WorkspaceActionBar({ terminalMinimized, onToggleTerminal }: Props) {
  const router = useRouter();
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const res = await fetch('http://localhost:8000/api/project/save', {
        method: 'POST',
      });

      if (!res.ok) throw new Error('Failed to save');

      const data = await res.json();
      if (data.ok && data.projectId) {
        // Redirect to dashboard with project ID
        window.location.href = `http://localhost:8080/agents?action=save&id=${data.projectId}`;
      }
    } catch (error) {
      console.error('Failed to save project:', error);
      alert('Failed to save project');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="h-14 flex items-center justify-between px-4 bg-background border-t border-border">
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleTerminal}
          className="px-3 py-1.5 text-xs bg-muted hover:bg-muted/80 text-muted-foreground rounded transition-colors border border-border"
        >
          {terminalMinimized ? 'Show Terminal' : 'Minimize Terminal'}
        </button>
      </div>

      <div className="flex items-center gap-3">
        <ConnectButton accountStatus="avatar" chainStatus="icon" showBalance={false} />

        <div className="h-6 w-px bg-border mx-1" />

        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-4 py-1.5 text-sm bg-primary hover:bg-emerald-glow text-primary-foreground font-semibold rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(16,185,129,0.2)]"
        >
          {isSaving ? 'Saving...' : 'Save to Dashboard'}
        </button>
      </div>
    </div>
  );
}

