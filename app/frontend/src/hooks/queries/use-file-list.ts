import { useQuery } from '@tanstack/react-query';
import { getFileList } from '@/lib/api';

export const useFileList = () => {
  return useQuery({
    queryKey: ['file-list'],
    queryFn: getFileList,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
};

