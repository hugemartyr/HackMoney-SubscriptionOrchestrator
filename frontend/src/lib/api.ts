import { FileSystemNode } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function uploadProject(githubUrl: string): Promise<{ success: boolean; name?: string }> {
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ github_url: githubUrl }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to upload project' }));
    throw new Error(errorData.detail || 'Failed to upload project');
  }

  const data = await response.json();
  // Extract repo name from GitHub URL for display
  const repoMatch = githubUrl.match(/github\.com\/([^/]+)\/([^/]+)/);
  const repoName = repoMatch ? repoMatch[2] : 'project';

  return {
    success: data.ok || true,
    name: repoName,
  };
}

export async function getFileTree(): Promise<FileSystemNode> {
  const response = await fetch(`${API_BASE_URL}/files/tree`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to load file tree' }));
    throw new Error(errorData.detail || 'Failed to load file tree');
  }

  const data = await response.json();
  return data.tree;
}

export async function getFileContent(path: string): Promise<{ path: string; content: string }> {
  const encodedPath = encodeURIComponent(path);
  const response = await fetch(`${API_BASE_URL}/files/content?path=${encodedPath}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to load file content' }));
    throw new Error(errorData.detail || 'Failed to load file content');
  }

  return response.json();
}

export async function putFileContent(path: string, content: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/files/content`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ path, content }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to save file' }));
    throw new Error(errorData.detail || 'Failed to save file');
  }
}

export async function deleteFile(path: string): Promise<void> {
  const encodedPath = encodeURIComponent(path);
  const response = await fetch(`${API_BASE_URL}/files?path=${encodedPath}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to delete file' }));
    throw new Error(errorData.detail || 'Failed to delete file');
  }
}

export async function approveDiff(file: string, approved: boolean, runId?: string | null): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/diff/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ runId: runId || null, file, approved }),
  });

  if (!response.ok) {
    throw new Error('Failed to approve/reject diff');
  }
}

export async function applyAllDiffs(
  approved: boolean,
  runId?: string | null,
): Promise<{ ok: boolean; applied: number }> {
  const response = await fetch(`${API_BASE_URL}/api/yellow-agent/apply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ runId: runId || null, approved }),
  });

  if (!response.ok) {
    throw new Error('Failed to apply/reject all diffs');
  }

  return response.json();
}

/**
 * Resume the agent after HITL approval. Returns the fetch Response so the caller
 * can read the SSE stream body. The backend applies diffs if approved, then continues execution.
 */
export function resumeAgentFetch(runId: string, approved: boolean): Promise<Response> {
  return fetch(`${API_BASE_URL}/api/yellow-agent/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ runId, approved }),
  });
}

export async function downloadProject(): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/project/download`, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new Error('Failed to download project');
  }

  return response.blob();
}

export async function runTerminalCommand(
  command: string,
): Promise<{ stdout: string[]; stderr: string[]; exitCode: number }> {
  const response = await fetch(`${API_BASE_URL}/api/terminal/exec`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ command }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to run terminal command' }));
    throw new Error(errorData.detail || 'Failed to run terminal command');
  }

  return response.json();
}
