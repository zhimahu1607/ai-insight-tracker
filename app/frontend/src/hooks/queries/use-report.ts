import { useQuery } from '@tanstack/react-query';
import { getReport } from '@/lib/api';

export const useReport = (dateOrFilename: string) => {
  return useQuery({
    queryKey: ['report', dateOrFilename],
    queryFn: () => getReport(dateOrFilename),
    enabled: !!dateOrFilename,
  });
};

