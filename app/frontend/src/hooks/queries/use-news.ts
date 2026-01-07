import { useQuery } from '@tanstack/react-query';
import { getNews } from '@/lib/api';

export const useNews = (date: string) => {
  return useQuery({
    queryKey: ['news', date],
    queryFn: () => getNews(date),
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: !!date,
    retry: 1,
  });
};

