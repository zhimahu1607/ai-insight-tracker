import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, FileSearch, ExternalLink, ScrollText } from "lucide-react";
import { useDeepAnalysis } from '@/hooks/queries/use-deep-analysis';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
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

// 自定义 Markdown 渲染组件
const MarkdownComponents: any = {
  h1: ({ ...props }) => <h1 className="text-3xl font-bold tracking-tight mt-10 mb-6 pb-2 border-b border-border scroll-m-20 first:mt-0" {...props} />,
  h2: ({ ...props }) => <h2 className="text-2xl font-semibold tracking-tight mt-10 mb-4 scroll-m-20 pb-1 border-b border-border/50" {...props} />,
  h3: ({ ...props }) => <h3 className="text-xl font-semibold tracking-tight mt-8 mb-3 scroll-m-20" {...props} />,
  h4: ({ ...props }) => <h4 className="text-lg font-semibold tracking-tight mt-6 mb-2 scroll-m-20" {...props} />,
  p: ({ ...props }) => <p className="leading-7 [&:not(:first-child)]:mt-4 text-foreground/90 text-base" {...props} />,
  blockquote: ({ ...props }) => (
    <blockquote className="mt-6 border-l-4 border-primary pl-6 py-2 italic bg-muted/40 rounded-r-lg text-muted-foreground" {...props} />
  ),
  ul: ({ ...props }) => <ul className="my-6 ml-6 list-disc [&>li]:mt-2 text-foreground/90" {...props} />,
  ol: ({ ...props }) => <ol className="my-6 ml-6 list-decimal [&>li]:mt-2 text-foreground/90" {...props} />,
  li: ({ ...props }) => <li className="leading-7" {...props} />,
  a: ({ ...props }) => <a className="font-medium text-primary underline underline-offset-4 hover:text-primary/80 transition-colors" {...props} target="_blank" rel="noopener noreferrer" />,
  hr: ({ ...props }) => <hr className="my-8 border-border" {...props} />,
  img: ({ ...props }) => <img className="rounded-lg border border-border my-6 shadow-sm" {...props} />,
  table: ({ ...props }) => <div className="my-6 w-full overflow-y-auto rounded-lg border border-border shadow-sm"><table className="w-full text-sm" {...props} /></div>,
  thead: ({ ...props }) => <thead className="bg-muted/50" {...props} />,
  tbody: ({ ...props }) => <tbody className="[&_tr:last-child]:border-0" {...props} />,
  tr: ({ ...props }) => <tr className="border-b border-border transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted" {...props} />,
  th: ({ ...props }) => <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0" {...props} />,
  td: ({ ...props }) => <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0" {...props} />,
  pre: ({ ...props }) => <pre className="mb-4 mt-6 overflow-x-auto rounded-lg border bg-zinc-950 dark:bg-zinc-900 py-4" {...props} />, 
  code: ({ inline, className, children, ...props }: any) => {
    if (inline) {
       return <code className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold text-foreground" {...props}>{children}</code>
    }
    // Block code (handled by rehype-highlight, but we add some base styles)
    return <code className={`${className} relative rounded bg-transparent px-[0.3rem] py-[0.2rem] font-mono text-sm`} {...props}>{children}</code>
  },
};

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

        <Sheet open={isOpen} onOpenChange={setIsOpen}>
          <SheetContent className="sm:max-w-[900px] w-full flex flex-col p-0 gap-0">
            <SheetHeader className="p-6 border-b">
              <SheetTitle className="text-2xl font-bold">Deep Analysis Report</SheetTitle>
              <SheetDescription>
                 {paperTitle} (ID: {paperId})
              </SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto p-6 md:p-10 h-full bg-background">
                <div className="max-w-4xl mx-auto pb-20">
                    <Markdown 
                        rehypePlugins={[rehypeHighlight]}
                        components={MarkdownComponents}
                    >
                        {data.content}
                    </Markdown>
                </div>
            </div>
          </SheetContent>
        </Sheet>
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

