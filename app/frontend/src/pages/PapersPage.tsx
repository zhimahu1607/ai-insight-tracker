import { useState, useEffect } from 'react';
import { PaperList } from '@/components/business/PaperList';
import { usePapers } from '@/hooks/queries/use-papers';
import { useFileList } from '@/hooks/queries/use-file-list';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from 'lucide-react';

const CATEGORIES = ['All', 'cs.AI', 'cs.CL', 'cs.CV', 'cs.LG'];
const ITEMS_PER_PAGE = 30;

export function PapersPage() {
  const { data: fileList, isLoading: isFileListLoading } = useFileList();
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedCategory, setSelectedCategory] = useState('All');
  
  // Set default date to latest when file list is loaded
  useEffect(() => {
    if (fileList?.papers && fileList.papers.length > 0 && !selectedDate) {
      const sortedDates = [...fileList.papers].sort().reverse();
      setSelectedDate(sortedDates[0]);
    }
  }, [fileList, selectedDate]);

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedDate, selectedCategory]);

  const { data: papers = [], isLoading: isPapersLoading } = usePapers(selectedDate);

  // If no dates available
  if (!isFileListLoading && (!fileList?.papers || fileList.papers.length === 0)) {
     return <div className="p-8 text-center text-muted-foreground">No paper data available.</div>
  }

  const handleDateChange = (date: string) => {
    setSelectedDate(date);
  };

  // Filter papers
  const filteredPapers = papers.filter(paper => {
    if (selectedCategory === 'All') return true;
    // Check primary category or categories list if available
    return paper.primary_category === selectedCategory || (paper.categories && paper.categories.includes(selectedCategory));
  });

  // Pagination
  const totalPages = Math.ceil(filteredPapers.length / ITEMS_PER_PAGE);
  const currentPapers = filteredPapers.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
             <h1 className="text-3xl font-bold tracking-tight">Papers</h1>
             <p className="text-muted-foreground mt-1">
               Discover and analyze the latest AI research papers.
             </p>
          </div>
          
          <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Date:</span>
              <Select value={selectedDate} onValueChange={handleDateChange}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Select date" />
                </SelectTrigger>
                <SelectContent>
                  {fileList?.papers?.slice().sort().reverse().map((filename) => (
                    <SelectItem key={filename} value={filename}>
                      {filename.replace(/\.jsonl?$/, '')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
          </div>
        </div>

        {/* Category Filter */}
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map(category => (
            <Button
              key={category}
              variant={selectedCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category)}
            >
              {category}
            </Button>
          ))}
          <div className="ml-auto text-sm text-muted-foreground self-center">
            Showing {filteredPapers.length} papers
          </div>
        </div>
      </div>

      <PaperList papers={currentPapers} isLoading={isPapersLoading || isFileListLoading} />

      {/* Pagination Controls */}
      {!isPapersLoading && totalPages > 1 && (
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
