import { useQuery } from '@tanstack/react-query';
import { getPapers } from '@/lib/api';

export const usePapers = (date: string) => {
  return useQuery({
    queryKey: ['papers', date],
    queryFn: () => getPapers(date),
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!date,          // only fetch if date is present
    retry: 1,
  });
};

