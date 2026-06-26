import { ReactNode } from "react";
import { VirtuosoGrid } from "react-virtuoso";

import { Skeleton } from "@/components/ui/skeleton";

interface DataGridListProps<T> {
  items: T[];
  isLoading: boolean;
  emptyMessage: string;
  skeletonCount: number;
  getKey: (item: T) => string;
  renderItem: (item: T) => ReactNode;
}

export function DataGridList<T>({
  items,
  isLoading,
  emptyMessage,
  skeletonCount,
  getKey,
  renderItem,
}: DataGridListProps<T>) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: skeletonCount }).map((_, index) => (
          <div key={index} className="space-y-3">
            <Skeleton className="h-[200px] w-full rounded-xl" />
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return <div className="py-12 text-center text-muted-foreground">{emptyMessage}</div>;
  }

  return (
    <VirtuosoGrid
      useWindowScroll
      data={items}
      totalCount={items.length}
      overscan={200}
      listClassName="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-8"
      itemContent={(_, item) => <>{renderItem(item)}</>}
      computeItemKey={(_, item) => getKey(item)}
    />
  );
}
