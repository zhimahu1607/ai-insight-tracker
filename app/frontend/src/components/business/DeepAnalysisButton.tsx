import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, FileSearch, ExternalLink, ScrollText } from "lucide-react";
import { useDeepAnalysis } from '@/hooks/queries/use-deep-analysis';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import Markdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css'; // You might need to import this style or another one

const GITHUB_REPO = import.meta.env.VITE_GITHUB_REPO || 'zhimahu1607/ai-insight-tracker';

interface DeepAnalysisButtonProps {
  paperId: string;
  paperTitle: string;
  className?: string;
  size?: "default" | "sm" | "lg" | "icon";
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
}

export function DeepAnalysisButton({ paperId, paperTitle, className, size = "sm", variant = "outline" }: DeepAnalysisButtonProps) {
  const { data, isLoading } = useDeepAnalysis(paperId);
  const [isOpen, setIsOpen] = useState(false);

  // 构建 GitHub Issue URL
  const handleCreateIssue = (e: React.MouseEvent) => {
    e.stopPropagation(); // 防止冒泡触发父级点击
    
    const title = `[Analysis] ${paperId}: ${paperTitle}`;
    const body = `Please analyze this paper.\n\nPaper ID: ${paperId}\nTitle: ${paperTitle}\n\n(Auto-generated request)`;
    const labels = 'agent-task';
    
    const url = `https://github.com/${GITHUB_REPO}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}&labels=${labels}`;
    window.open(url, '_blank');
  };

  const handleOpenReport = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(true);
  };

  const showText = size !== 'icon';

  if (isLoading) {
    return (
      <Button variant="ghost" size={size} disabled className={className}>
        <Loader2 className={`w-4 h-4 animate-spin ${showText ? 'mr-2' : ''}`} />
        {showText && "Checking..."}
      </Button>
    );
  }

  if (data?.status === 'completed') {
    return (
      <>
        <Button 
            variant="default" 
            size={size} 
            className={`${className} bg-green-600 hover:bg-green-700 text-white border-transparent`}
            onClick={handleOpenReport}
            title="View Deep Analysis Report"
        >
          <ScrollText className={`w-4 h-4 ${showText ? 'mr-2' : ''}`} />
          {showText && "Deep Analysis Report"}
        </Button>

        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold mb-4">Deep Analysis Report</DialogTitle>
              <DialogDescription>
                 {paperTitle} (ID: {paperId})
              </DialogDescription>
            </DialogHeader>
            <div className="prose prose-sm sm:prose-base dark:prose-invert max-w-none">
              <Markdown rehypePlugins={[rehypeHighlight]}>
                {data.content}
              </Markdown>
            </div>
          </DialogContent>
        </Dialog>
      </>
    );
  }

  if (data?.status === 'processing') {
    return (
      <Button variant="secondary" size={size} disabled className={`${className} cursor-not-allowed opacity-80`} title="Analysis in progress...">
        <Loader2 className={`w-4 h-4 animate-spin ${showText ? 'mr-2' : ''}`} />
        {showText && "Analyzing..."}
      </Button>
    );
  }

  // Pending status
  return (
    <Button 
        variant={variant} 
        size={size} 
        className={className} 
        onClick={handleCreateIssue}
        title="Request Deep Analysis"
    >
      <FileSearch className={`w-4 h-4 ${showText ? 'mr-2' : ''}`} />
      {showText && "Deep Analysis"}
    </Button>
  );
}

