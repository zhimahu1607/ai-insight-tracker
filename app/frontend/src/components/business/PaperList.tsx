import { AnalyzedPaper } from "@/types";
import { PaperCard } from "./PaperCard";
import { VirtuosoGrid } from "react-virtuoso";
import { Skeleton } from "@/components/ui/skeleton";

interface PaperListProps {
  papers: AnalyzedPaper[];
  isLoading: boolean;
}

export function PaperList({ papers, isLoading }: PaperListProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array(6).fill(0).map((_, i) => (
          <div key={i} className="space-y-3">
             <Skeleton className="h-[200px] w-full rounded-xl" />
          </div>
        ))}
      </div>
    );
  }

  if (papers.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No papers found.
      </div>
    );
  }

  return (
    <VirtuosoGrid
      useWindowScroll
      data={papers}
      totalCount={papers.length}
      overscan={200}
      listClassName="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-8"
      itemContent={(index, paper) => (
         <PaperCard key={paper.id} paper={paper} />
      )}
    />
  );
}

