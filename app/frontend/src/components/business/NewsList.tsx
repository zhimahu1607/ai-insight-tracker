import { AnalyzedNews } from "@/types";
import { DataGridList } from "./DataGridList";
import { NewsCard } from "./NewsCard";

interface NewsListProps {
  news: AnalyzedNews[];
  isLoading: boolean;
}

export function NewsList({ news, isLoading }: NewsListProps) {
  return (
    <DataGridList
      items={news}
      isLoading={isLoading}
      emptyMessage="No news found."
      skeletonCount={8}
      getKey={(item) => item.id}
      renderItem={(item) => <NewsCard news={item} />}
    />
  );
}
