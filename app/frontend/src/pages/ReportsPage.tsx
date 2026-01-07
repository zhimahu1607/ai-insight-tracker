import { useState, useEffect } from 'react';
import { useReport } from '@/hooks/queries/use-report';
import { useFileList } from '@/hooks/queries/use-file-list';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { FileText, Newspaper, Calendar, TrendingUp, Hash, PieChart } from "lucide-react";

export function ReportsPage() {
  const { data: fileList, isLoading: isFileListLoading } = useFileList();
  const [selectedDate, setSelectedDate] = useState<string>('');
  
  // Set default date to latest when file list is loaded
  useEffect(() => {
    if (fileList?.reports && fileList.reports.length > 0 && !selectedDate) {
      const sortedDates = [...fileList.reports].sort().reverse();
      setSelectedDate(sortedDates[0]);
    }
  }, [fileList, selectedDate]);

  const { data: report, isLoading: isReportLoading } = useReport(selectedDate);

  // If no dates available
  if (!isFileListLoading && (!fileList?.reports || fileList.reports.length === 0)) {
     return <div className="p-8 text-center text-muted-foreground">No report data available.</div>
  }

  const handleDateChange = (date: string) => {
    setSelectedDate(date);
  };

  const isLoading = isFileListLoading || isReportLoading;

  const stats = report?.stats || {
    total_papers: 0,
    papers_by_category: {},
    total_news: 0,
    news_by_category: {},
    top_keywords: []
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
           <h1 className="text-3xl font-bold tracking-tight">Daily Reports</h1>
           <p className="text-muted-foreground mt-1">
             AI-generated daily summary of papers and news.
           </p>
        </div>
        
        <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Date:</span>
            <Select value={selectedDate} onValueChange={handleDateChange}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select date" />
              </SelectTrigger>
              <SelectContent>
                {fileList?.reports?.slice().sort().reverse().map((filename) => (
                  <SelectItem key={filename} value={filename}>
                    {filename.replace('.json', '')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : report ? (
        <div className="space-y-6">
          {/* Stats Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Papers</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_papers}</div>
                <div className="flex flex-wrap gap-1 mt-2">
                   {stats.papers_by_category && Object.entries(stats.papers_by_category).map(([cat, count]) => (
                     <Badge key={cat} variant="secondary" className="text-[10px] px-1 h-5">
                       {cat}: {count}
                     </Badge>
                   ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">News</CardTitle>
                <Newspaper className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_news}</div>
                 <div className="flex flex-wrap gap-1 mt-2">
                   {stats.news_by_category && Object.entries(stats.news_by_category).map(([cat, count]) => (
                     <Badge key={cat} variant="secondary" className="text-[10px] px-1 h-5">
                       {cat}: {count}
                     </Badge>
                   ))}
                </div>
              </CardContent>
            </Card>
            
            <Card className="md:col-span-2">
               <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Keywords</CardTitle>
                <Hash className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                 <div className="flex flex-wrap gap-1 mt-1">
                   {stats.top_keywords?.slice(0, 10).map(keyword => (
                     <Badge key={keyword} variant="outline" className="text-[10px] px-2 h-6">
                       {keyword}
                     </Badge>
                   ))}
                 </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Summary */}
          <Card className="border-l-4 border-l-primary">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                Daily Overview
              </CardTitle>
              <CardDescription>AI-generated executive summary of the day's research and news.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="prose dark:prose-invert max-w-none whitespace-pre-wrap text-sm leading-relaxed">
                {report.summary || 'No summary available.'}
              </div>
            </CardContent>
          </Card>
          
          {/* News Summary */}
          {report.news_summary && (
             <Card className="border-l-4 border-l-primary">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Newspaper className="h-5 w-5" />
                  News Highlights
                </CardTitle>
              </CardHeader>
              <CardContent>
                 <div className="prose dark:prose-invert max-w-none whitespace-pre-wrap text-sm leading-relaxed">
                  {report.news_summary}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Category Summaries Grid */}
          {report.category_summaries && Object.keys(report.category_summaries).length > 0 && (
             <div>
                <h2 className="text-xl font-semibold tracking-tight mb-4 flex items-center gap-2">
                  <PieChart className="h-5 w-5" />
                  Research Categories
                </h2>
                <div className="grid gap-6">
                  {Object.entries(report.category_summaries).map(([category, summary]) => (
                    <Card key={category} className="border-l-4 border-l-primary">
                      <CardHeader>
                        <CardTitle className="text-lg">{category}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="prose dark:prose-invert max-w-none whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                          {summary}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
             </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          No report found for this date.
        </div>
      )}
    </div>
  );
}
