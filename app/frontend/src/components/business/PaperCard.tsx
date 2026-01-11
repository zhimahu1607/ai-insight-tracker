import { AnalyzedPaper } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogTrigger, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ExternalLink, Calendar, Users, FileText, Lightbulb, Zap, Target, Flag } from "lucide-react";
import { DeepAnalysisButton } from "./DeepAnalysisButton";

interface PaperCardProps {
  paper: AnalyzedPaper;
}

export function PaperCard({ paper }: PaperCardProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Card className="hover:shadow-md transition-shadow cursor-pointer h-full flex flex-col text-left">
          <CardHeader className="pb-3 space-y-2">
            <div className="flex justify-between items-start gap-2">
              <Badge variant="secondary" className="font-mono text-xs">
                {paper.primary_category}
              </Badge>
              <div onClick={(e) => e.stopPropagation()}>
                <DeepAnalysisButton paperId={paper.id} paperTitle={paper.title} size="sm" className="h-7 text-xs px-2" />
              </div>
            </div>
            <CardTitle className="text-lg leading-tight line-clamp-2">
              {paper.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1">
            <p className="text-sm text-muted-foreground line-clamp-4">
              {paper.light_analysis?.overview ?? paper.abstract}
            </p>
          </CardContent>
        </Card>
      </DialogTrigger>
      
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-2">
             <Badge>{paper.primary_category}</Badge>
             <span className="text-sm text-muted-foreground flex items-center">
                <Calendar className="w-3 h-3 mr-1" />
                {paper.published.split('T')[0]}
             </span>
             <div className="ml-auto">
                <DeepAnalysisButton paperId={paper.id} paperTitle={paper.title} />
             </div>
          </div>
          <DialogTitle className="text-xl sm:text-2xl leading-tight">{paper.title}</DialogTitle>
          <DialogDescription className="text-base mt-2">
             <div className="flex items-center gap-1 mb-2">
                <Users className="w-4 h-4" />
                <span>{paper.authors.join(", ")}</span>
             </div>
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6 mt-4">
          <div className="flex gap-2">
             <Button asChild size="sm" variant="outline">
                <a href={paper.pdf_url} target="_blank" rel="noreferrer">
                   <FileTextIcon className="w-4 h-4 mr-2" /> PDF
                </a>
             </Button>
             <Button asChild size="sm" variant="outline">
                <a href={`https://arxiv.org/abs/${paper.id}`} target="_blank" rel="noreferrer">
                   <ExternalLink className="w-4 h-4 mr-2" /> arXiv
                </a>
             </Button>
          </div>

          {paper.light_analysis && (
             <div className="space-y-4">
                <div className="bg-muted/50 p-4 rounded-lg space-y-3">
                   <h4 className="font-semibold flex items-center gap-2 text-primary">
                      <Lightbulb className="w-4 h-4" /> AI Analysis
                   </h4>
                   
                   <div className="grid gap-4 md:grid-cols-2">
                      <div className="col-span-2">
                         <span className="font-medium text-sm text-foreground/80 block mb-1">Overview</span>
                         <p className="text-sm leading-relaxed">{paper.light_analysis.overview}</p>
                      </div>
                      
                      {paper.light_analysis.motivation && (
                        <div>
                           <span className="font-medium text-sm text-foreground/80 flex items-center gap-1 mb-1">
                             <Target className="w-3 h-3" /> Motivation
                           </span>
                           <p className="text-sm text-muted-foreground">{paper.light_analysis.motivation}</p>
                        </div>
                      )}
                      
                      {paper.light_analysis.method && (
                        <div>
                           <span className="font-medium text-sm text-foreground/80 flex items-center gap-1 mb-1">
                             <Zap className="w-3 h-3" /> Method
                           </span>
                           <p className="text-sm text-muted-foreground">{paper.light_analysis.method}</p>
                        </div>
                      )}

                      {paper.light_analysis.result && (
                        <div>
                           <span className="font-medium text-sm text-foreground/80 flex items-center gap-1 mb-1">
                             <Flag className="w-3 h-3" /> Result
                           </span>
                           <p className="text-sm text-muted-foreground">{paper.light_analysis.result}</p>
                        </div>
                      )}
                      
                      {paper.light_analysis.conclusion && (
                        <div>
                           <span className="font-medium text-sm text-foreground/80 block mb-1">Conclusion</span>
                           <p className="text-sm text-muted-foreground">{paper.light_analysis.conclusion}</p>
                        </div>
                      )}
                   </div>

                   {paper.light_analysis.tags && (
                      <div className="pt-2 flex flex-wrap gap-1">
                         {paper.light_analysis.tags.map(tag => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                               {tag}
                            </Badge>
                         ))}
                      </div>
                   )}
                </div>
             </div>
          )}

          <div>
             <h4 className="font-semibold mb-2">Abstract</h4>
             <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
               {paper.abstract}
             </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Renamed locally to avoid conflict if I imported Lucide's FileText
function FileTextIcon({ className }: { className?: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" x2="8" y1="13" y2="13" />
            <line x1="16" x2="8" y1="17" y2="17" />
            <line x1="10" x2="8" y1="9" y2="9" />
        </svg>
    )
}
