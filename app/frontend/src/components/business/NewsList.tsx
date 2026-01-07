import { AnalyzedNews } from "@/types";
import { NewsCard } from "./NewsCard";
import { VirtuosoGrid } from "react-virtuoso";
import { Skeleton } from "@/components/ui/skeleton";

interface NewsListProps {
  news: AnalyzedNews[];
  isLoading: boolean;
}

export function NewsList({ news, isLoading }: NewsListProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array(8).fill(0).map((_, i) => (
          <div key={i} className="space-y-3">
             <Skeleton className="h-[200px] w-full rounded-xl" />
          </div>
        ))}
      </div>
    );
  }

  if (news.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No news found.
      </div>
    );
  }

  return (
    <VirtuosoGrid
      useWindowScroll
      data={news}
      totalCount={news.length}
      overscan={200}
      listClassName="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-8"
      itemContent={(index, item) => (
         <NewsCard key={item.id} news={item} />
      )}
    />
  );
}

