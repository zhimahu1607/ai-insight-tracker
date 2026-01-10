import { useQuery } from '@tanstack/react-query';
import { AnalysisStatus } from '@/types';

const BASE_URL = import.meta.env.BASE_URL;

interface DeepAnalysisStatus {
  status: 'pending' | 'processing' | 'completed';
  content?: string;
}

interface ProcessingStatus {
  processing_ids: string[];
}

export const useDeepAnalysis = (paperId: string) => {
  return useQuery({
    queryKey: ['deep-analysis', paperId],
    queryFn: async (): Promise<DeepAnalysisStatus> => {
      // 1. Check if completed analysis exists
      try {
        const res = await fetch(`${BASE_URL}data/analysis/deep/${paperId}.md`);
        if (res.ok) {
          const content = await res.text();
          return { status: 'completed', content };
        }
      } catch (e) {
        // ignore
      }

      // 2. Check if processing
      try {
        // Add timestamp to prevent caching
        const res = await fetch(`${BASE_URL}data/analysis/deep_analysis_status.json?t=${Date.now()}`);
        if (res.ok) {
          const data: ProcessingStatus = await res.json();
          if (data.processing_ids.includes(paperId)) {
            return { status: 'processing' };
          }
        }
      } catch (e) {
        // ignore
      }

      // 3. Default pending
      return { status: 'pending' };
    },
    retry: false,
    refetchOnWindowFocus: true, // Refresh when coming back (e.g. from GitHub)
  });
};

