import { useState, useEffect } from 'react';
import { NewsList } from '@/components/business/NewsList';
import { useNews } from '@/hooks/queries/use-news';
import { useFileList } from '@/hooks/queries/use-file-list';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from 'lucide-react';

const ITEMS_PER_PAGE = 30;

export function NewsPage() {
  const { data: fileList, isLoading: isFileListLoading } = useFileList();
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  
  // Set default date to latest when file list is loaded
  useEffect(() => {
    if (fileList?.news && fileList.news.length > 0 && !selectedDate) {
      const sortedDates = [...fileList.news].sort().reverse();
      setSelectedDate(sortedDates[0]);
    }
  }, [fileList, selectedDate]);

  // Reset page when date changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedDate]);

  const { data: news = [], isLoading: isNewsLoading } = useNews(selectedDate);

  // If no dates available
  if (!isFileListLoading && (!fileList?.news || fileList.news.length === 0)) {
     return <div className="p-8 text-center text-muted-foreground">No news data available.</div>
  }

  const handleDateChange = (date: string) => {
    setSelectedDate(date);
  };

  // Pagination
  const totalPages = Math.ceil(news.length / ITEMS_PER_PAGE);
  const currentNews = news.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
           <h1 className="text-3xl font-bold tracking-tight">News</h1>
           <p className="text-muted-foreground mt-1">
             Trending AI news and updates from various sources.
           </p>
        </div>
        
        <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Date:</span>
            <Select value={selectedDate} onValueChange={handleDateChange}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select date" />
              </SelectTrigger>
              <SelectContent>
                {fileList?.news?.slice().sort().reverse().map((filename) => (
                  <SelectItem key={filename} value={filename}>
                    {filename.replace(/\.jsonl?$/, '')}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
        </div>
      </div>

      <div className="flex justify-end text-sm text-muted-foreground">
        Showing {news.length} items
      </div>

      <NewsList news={currentNews} isLoading={isNewsLoading || isFileListLoading} />

      {/* Pagination Controls */}
      {!isNewsLoading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
