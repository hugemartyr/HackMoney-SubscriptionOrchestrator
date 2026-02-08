'use client';

import * as React from 'react';
import { Folder, FileCode, ChevronRight, ChevronDown } from "lucide-react";
import { useState } from 'react';
import { FileSystemNode } from '@/lib/types';
import { useProjectContext } from '@/context/ProjectContext';
import { getFileContent, deleteFile, putFileContent, getFileTree } from '@/lib/api';
import ContextMenu from './ContextMenu';

interface FileNodeProps {
  node: FileSystemNode;
  onSelect: (path: string) => void;
  onContextMenu: (e: React.MouseEvent, path: string, isFile: boolean) => void;
  currentFile: string | null;
}

const FileNode = ({ node, onSelect, onContextMenu, currentFile }: FileNodeProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const isSelected = currentFile === node.path;

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onContextMenu(e, node.path, node.type === 'file');
  };

  if (node.type === "file") {
    return (
      <div
        onClick={() => onSelect(node.path)}
        onContextMenu={handleContextMenu}
        className={`
          flex items-center gap-2 p-1 hover:bg-gray-800 cursor-pointer text-sm pl-4 overflow-hidden
          ${isSelected ? 'bg-gray-800 text-white' : 'text-gray-300'}
        `}
      >
        <FileCode size={14} className="text-blue-400 shrink-0" />
        <span className="truncate">{node.name}</span>
      </div>
    );
  }

  return (
    <div>
      <div
        onClick={() => setIsOpen(!isOpen)}
        onContextMenu={handleContextMenu}
        className="flex items-center gap-2 p-1 hover:bg-gray-800 cursor-pointer text-sm text-gray-100 font-bold overflow-hidden"
      >
        {isOpen ? <ChevronDown size={14} className="shrink-0" /> : <ChevronRight size={14} className="shrink-0" />}
        <Folder size={14} className="text-primary shrink-0" />
        <span className="truncate">{node.name}</span>
      </div>

      {isOpen && node.children && (
        <div className="pl-4 border-l border-gray-700 ml-2">
          {node.children.map((child) => (
            <FileNode
              key={child.path}
              node={child}
              onSelect={onSelect}
              onContextMenu={onContextMenu}
              currentFile={currentFile}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default function FileTree() {
  const { state, openFile, updateFileContent, updateFileTree, closeFile } = useProjectContext();
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; path: string; isFile: boolean } | null>(null);

  const handleSelect = async (path: string) => {
    openFile(path);

    // If file content not cached, fetch it
    if (!state.fileContents[path]) {
      try {
        const { content } = await getFileContent(path);
        updateFileContent(path, content);
      } catch (err) {
        console.error('Failed to load file:', err);
        // Set empty content as fallback
        updateFileContent(path, `// Error loading file: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    }
  };

  const handleContextMenu = (e: React.MouseEvent, path: string, isFile: boolean) => {
    setContextMenu({ x: e.clientX, y: e.clientY, path, isFile });
  };

  const handleNewFile = async () => {
    if (!contextMenu) return;

    const parentPath = contextMenu.isFile
      ? contextMenu.path.split('/').slice(0, -1).join('/') || ''
      : contextMenu.path;

    const fileName = prompt('Enter file name:');
    if (!fileName || !fileName.trim()) return;

    const newPath = parentPath ? `${parentPath}/${fileName.trim()}` : fileName.trim();

    try {
      // Create empty file
      await putFileContent(newPath, '');

      // Refresh file tree
      const tree = await getFileTree();
      updateFileTree(tree);

      // Open the new file
      openFile(newPath);
      updateFileContent(newPath, '');
    } catch (err) {
      alert(`Failed to create file: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleDelete = async () => {
    if (!contextMenu || !contextMenu.isFile) return;

    const confirmed = confirm(`Are you sure you want to delete ${contextMenu.path}?`);
    if (!confirmed) return;

    try {
      await deleteFile(contextMenu.path);

      // Close file if it's open
      if (state.openFiles.includes(contextMenu.path)) {
        closeFile(contextMenu.path);
      }

      // Refresh file tree
      const tree = await getFileTree();
      updateFileTree(tree);
    } catch (err) {
      alert(`Failed to delete file: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (!state.fileTree) {
    return (
      <div className="w-full h-full overflow-y-auto p-2">
        <div className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">
          Explorer
        </div>
        <div className="text-gray-500 text-sm p-4">
          No files loaded yet
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="w-full h-full overflow-y-auto p-2">
        <div className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">
          Explorer
        </div>
        <FileNode
          node={state.fileTree}
          onSelect={handleSelect}
          onContextMenu={handleContextMenu}
          currentFile={state.currentFile}
        />
      </div>

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          onNewFile={handleNewFile}
          onDelete={contextMenu.isFile ? handleDelete : undefined}
          isFile={contextMenu.isFile}
        />
      )}
    </>
  );
}
