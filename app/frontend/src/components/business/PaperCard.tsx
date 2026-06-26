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
  const trackingScore = paper.tracking_score ?? paper.quality_score;
  const source = paper.source ?? "arxiv";
  const canRequestDeepAnalysis = source === "arxiv" && !paper.id.startsWith("openreview:");
  const paperUrl = paper.abs_url ?? `https://arxiv.org/abs/${paper.id}`;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Card className="hover:shadow-md transition-shadow cursor-pointer h-full flex flex-col text-left">
          <CardHeader className="pb-3 space-y-2">
            <div className="flex justify-between items-start gap-2">
              <div className="flex flex-wrap gap-1">
                <Badge variant="secondary" className="font-mono text-xs">
                  {paper.primary_category}
                </Badge>
                {source !== "arxiv" && (
                  <Badge variant="outline" className="text-xs">
                    {source}
                  </Badge>
                )}
                {trackingScore !== undefined && (
                  <Badge variant="outline" className="text-xs">
                    Score {trackingScore.toFixed(1)}
                  </Badge>
                )}
              </div>
              {canRequestDeepAnalysis && (
                <div onClick={(e) => e.stopPropagation()}>
                  <DeepAnalysisButton paperId={paper.id} paperTitle={paper.title} size="sm" className="h-7 text-xs px-2" />
                </div>
              )}
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
             {trackingScore !== undefined && (
                <Badge variant="outline">Score {trackingScore.toFixed(1)}</Badge>
             )}
             {paper.quality_confidence && (
                <Badge variant="secondary">Confidence {paper.quality_confidence}</Badge>
             )}
             <span className="text-sm text-muted-foreground flex items-center">
                <Calendar className="w-3 h-3 mr-1" />
                {paper.published.split('T')[0]}
             </span>
             {canRequestDeepAnalysis && <div className="ml-auto">
                <DeepAnalysisButton paperId={paper.id} paperTitle={paper.title} />
             </div>}
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
                   <FileText className="w-4 h-4 mr-2" /> PDF
                </a>
             </Button>
             <Button asChild size="sm" variant="outline">
                <a href={paperUrl} target="_blank" rel="noreferrer">
                   <ExternalLink className="w-4 h-4 mr-2" /> Source
                </a>
             </Button>
          </div>

          {paper.quality_reasons && paper.quality_reasons.length > 0 && (
             <div className="bg-muted/50 p-4 rounded-lg">
                <h4 className="font-semibold mb-2">Quality Signals</h4>
                <div className="flex flex-wrap gap-2">
                  {paper.quality_reasons.map(reason => (
                    <Badge key={reason} variant="secondary" className="text-xs">
                      {reason}
                    </Badge>
                  ))}
                </div>
             </div>
          )}

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
