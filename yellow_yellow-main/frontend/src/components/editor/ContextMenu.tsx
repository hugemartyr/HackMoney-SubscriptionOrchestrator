'use client';

import React from 'react';
import { FilePlus, Trash2 } from 'lucide-react';

interface ContextMenuProps {
  x: number;
  y: number;
  onClose: () => void;
  onNewFile: () => void;
  onDelete?: () => void;
  isFile: boolean;
}

export default function ContextMenu({ x, y, onClose, onNewFile, onDelete, isFile }: ContextMenuProps) {
  React.useEffect(() => {
    const handleClickOutside = () => onClose();
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  return (
    <div
      className="fixed bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50 min-w-[180px] py-1"
      style={{ left: `${x}px`, top: `${y}px` }}
      onClick={(e) => e.stopPropagation()}
    >
      <button
        onClick={(e) => {
          e.stopPropagation();
          onNewFile();
          onClose();
        }}
        className="w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 flex items-center gap-2"
      >
        <FilePlus size={14} />
        New File
      </button>
      {isFile && onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
            onClose();
          }}
          className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-gray-700 flex items-center gap-2"
        >
          <Trash2 size={14} />
          Delete
        </button>
      )}
    </div>
  );
}
