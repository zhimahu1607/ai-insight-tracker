import { AnalyzedPaper } from "@/types";
import { DataGridList } from "./DataGridList";
import { PaperCard } from "./PaperCard";

interface PaperListProps {
  papers: AnalyzedPaper[];
  isLoading: boolean;
}

export function PaperList({ papers, isLoading }: PaperListProps) {
  return (
    <DataGridList
      items={papers}
      isLoading={isLoading}
      emptyMessage="No papers found."
      skeletonCount={6}
      getKey={(paper) => paper.id}
      renderItem={(paper) => <PaperCard paper={paper} />}
    />
  );
}
