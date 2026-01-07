import { AnalyzedNews } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink } from "lucide-react";

interface NewsCardProps {
  news: AnalyzedNews;
}

export function NewsCard({ news }: NewsCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow h-full flex flex-col">
      <CardHeader className="pb-3 space-y-2">
        <div className="flex justify-between items-start gap-2">
           <div className="flex gap-2">
              <Badge variant="outline">{news.source_name}</Badge>
              {news.light_analysis && (
                <Badge variant="secondary">{news.light_analysis.category}</Badge>
              )}
           </div>
        </div>
        <CardTitle className="text-lg leading-tight line-clamp-2">
          <a href={news.url} target="_blank" rel="noreferrer" className="hover:underline flex items-start gap-1">
             {news.title}
             <ExternalLink className="w-4 h-4 mt-1 shrink-0 opacity-50" />
          </a>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
        <p className="text-sm text-muted-foreground line-clamp-3 mb-3 flex-1">
          {news.light_analysis?.summary ?? news.summary}
        </p>
        
        {news.light_analysis?.keywords && (
             <div className="flex flex-wrap gap-1 mt-auto pt-2">
              {news.light_analysis.keywords.slice(0, 3).map((keyword) => (
                <Badge key={keyword} variant="outline" className="text-[10px] h-5 px-1.5">
                  {keyword}
                </Badge>
              ))}
            </div>
        )}
        
        <div className="flex justify-between items-center mt-3 pt-2 border-t text-xs text-muted-foreground">
             <span>{new Date(news.published).toLocaleDateString()}</span>
             {news.light_analysis?.sentiment && (
                 <span className={
                    news.light_analysis.sentiment === 'positive' ? 'text-green-600' :
                    news.light_analysis.sentiment === 'negative' ? 'text-red-600' : 'text-gray-500'
                 }>
                    {news.light_analysis.sentiment}
                 </span>
             )}
        </div>
      </CardContent>
    </Card>
  );
}
