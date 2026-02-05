'use client';

import React, { useState } from 'react';
import { Github, Loader2 } from 'lucide-react';
import { uploadProject, getFileTree } from '@/lib/api';
import { useProjectContext } from '@/context/ProjectContext';

export default function ProjectUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [githubUrl, setGithubUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { markProjectUploaded, updateFileTree } = useProjectContext();

  const handleGithubUpload = async () => {
    if (!githubUrl.trim()) {
      setError('Please enter a GitHub URL');
      return;
    }
    
    setIsUploading(true);
    setError(null);
    
    try {
      const result = await uploadProject(githubUrl.trim());
      markProjectUploaded(result.name || 'project');
      
      // Load file tree immediately after upload
      try {
        const tree = await getFileTree();
        updateFileTree(tree);
      } catch (err) {
        console.error('Failed to load file tree:', err);
        // Don't block navigation, but log error
        // User can still proceed and files will load when they click
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isUploading && githubUrl.trim()) {
      handleGithubUpload();
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
      <div className="max-w-2xl w-full space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">
            Yellow-fier
          </h1>
          <p className="text-gray-400">
            Transform your app to use Yellow Network State Channels
          </p>
        </div>

        {/* GitHub URL Input */}
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-8">
            <div className="flex items-center gap-3 mb-4">
              <Github size={24} className="text-yellow-500" />
              <h2 className="text-xl font-semibold">Import from GitHub</h2>
            </div>
            <p className="text-sm text-gray-400 mb-6">
              Enter a GitHub repository URL to get started. We'll clone the repo and set up your project in a secure sandbox.
            </p>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Github className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="https://github.com/username/repo"
                  className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 text-white placeholder-gray-500"
                  disabled={isUploading}
                />
              </div>
              <button
                onClick={handleGithubUpload}
                disabled={isUploading || !githubUrl.trim()}
                className="px-6 py-3 bg-yellow-500 hover:bg-yellow-400 text-black font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="animate-spin" size={16} />
                    Cloning...
                  </>
                ) : (
                  'Import'
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Info */}
        <div className="text-center text-sm text-gray-500 space-y-1">
          <p>Your code runs in a secure cloud sandbox</p>
          <p>We never store or access your code outside the session</p>
          <p className="text-xs text-gray-600 mt-2">
            Format: https://github.com/owner/repository
          </p>
        </div>
      </div>
    </div>
  );
}
