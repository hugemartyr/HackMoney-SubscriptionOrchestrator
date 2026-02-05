import { useRef } from 'react';
// import { editor } from 'monaco-editor';

// We define a simplified interface to avoid importing the heavy 'monaco-editor' package in hooks if unnecessary, 
// or ensure proper type importing. Use 'import type' for best practice.
import type { editor } from 'monaco-editor';

export function useEditorContext() {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleEditorDidMount = (editorInstance: editor.IStandaloneCodeEditor) => {
    editorRef.current = editorInstance;
  };

  const getContext = () => {
    if (!editorRef.current) return null;

    const model = editorRef.current.getModel();
    if (!model) return null;

    const selection = editorRef.current.getSelection();
    if (!selection) return null;
    
    // Only get range if selection is not empty to avoid errors
    const selectedText = model.getValueInRange(selection);
    const position = editorRef.current.getPosition();
    const fullContent = model.getValue();

    const isSelectionActive = selectedText.length > 5;

    return {
      filePath: "src/App.tsx", // Placeholder until file tree is connected
      language: model.getLanguageId(),
      cursorLine: position?.lineNumber || 1,
      primaryContent: isSelectionActive ? selectedText : fullContent,
      isFragment: isSelectionActive
    };
  };

  return { handleEditorDidMount, getContext };
}
