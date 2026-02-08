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
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4">
      <div className="max-w-2xl w-full space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-emerald to-primary bg-clip-text text-transparent drop-shadow-[0_0_15px_rgba(16,185,129,0.3)]">
            Yellow Agent Factory
          </h1>
          <p className="text-muted-foreground">
            Transform your app with Yellow Network State Channels
          </p>
        </div>

        {/* GitHub URL Input */}
        <div className="space-y-4">
          <div className="bg-card/60 backdrop-blur-sm border border-border rounded-xl p-8 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <Github size={24} className="text-primary" />
              <h2 className="text-xl font-semibold">Import from GitHub</h2>
            </div>
            <p className="text-sm text-muted-foreground mb-6">
              Enter a GitHub repository URL to get started. We'll clone the repo and set up your project in a secure sandbox.
            </p>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Github className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" size={20} />
                <input
                  type="text"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="https://github.com/username/repo"
                  className="w-full pl-12 pr-4 py-3 bg-muted/30 border border-border rounded-lg outline-none focus:ring-2 focus:ring-primary/50 text-foreground placeholder-muted-foreground transition-all"
                  disabled={isUploading}
                />
              </div>
              <button
                onClick={handleGithubUpload}
                disabled={isUploading || !githubUrl.trim()}
                className="px-6 py-3 bg-primary hover:bg-emerald-glow text-primary-foreground font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-[0_0_20px_rgba(16,185,129,0.2)]"
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
          <div className="p-4 bg-destructive/10 border border-destructive/50 rounded-lg text-destructive text-sm">
            {error}
          </div>
        )}

        {/* Info */}
        <div className="text-center text-sm text-muted-foreground space-y-1">
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
