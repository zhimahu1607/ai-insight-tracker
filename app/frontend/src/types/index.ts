export type AnalysisStatus = 'success' | 'failed' | 'pending';

// Paper Types
export interface PaperLightAnalysis {
  overview: string;
  motivation: string;
  method: string;
  result: string;
  conclusion: string;
  tags: string[];
}

export interface Paper {
  id: string; // arxiv id
  source?: string;
  external_ids?: {
    arxiv?: string;
    doi?: string;
    semantic_scholar?: string;
    openalex?: string;
    openreview?: string;
  };
  title: string;
  abstract: string;
  authors: string[];
  primary_category: string;
  categories: string[];
  published: string;
  updated: string;
  pdf_url: string;
  abs_url?: string;
  version: string;
  quality_score?: number;
  relevance_score?: number;
  tracking_score?: number;
  quality_confidence?: 'high' | 'medium' | 'low';
  quality_reasons?: string[];
  quality_signals?: {
    sources?: string[];
    semantic_scholar?: {
      citation_count?: number;
      influential_citation_count?: number;
      venue?: string;
    };
    papers_with_code?: {
      has_code?: boolean;
      repositories?: Array<{
        url: string;
        stars?: number;
        is_official?: boolean;
      }>;
    };
    openalex?: {
      cited_by_count?: number;
      fwci?: number;
      institutions?: string[];
      source?: string;
    };
    openreview?: {
      venue_id?: string;
      decision?: string;
      rating_avg?: number;
      confidence_avg?: number;
      review_count?: number;
    };
  };
}

export interface AnalyzedPaper extends Paper {
  light_analysis?: PaperLightAnalysis;
  analysis_status: AnalysisStatus;
  analyzed_at?: string;
}

// News Types
export interface NewsLightAnalysis {
  summary: string;
  category: "AI" | "LLM" | "开源" | "产品" | "行业" | "其他";
  sentiment: "positive" | "neutral" | "negative";
  keywords: string[];
}

export interface NewsItem {
  id: string;
  title: string;
  url: string;
  source_name: string;
  source_category: string;
  language: string;
  published: string;
  summary?: string;
  weight: number;
}

export interface AnalyzedNews extends NewsItem {
  light_analysis?: NewsLightAnalysis;
  analyzed_at?: string;
  analysis_status: AnalysisStatus;
  analysis_error?: string;
}

// File List
export interface FileList {
  papers: string[]; // list of dates YYYY-MM-DD
  news: string[];
  reports: string[];
  last_updated: string;
}

// Daily Report
export interface DailyReport {
  date: string;
  summary: string;
  category_summaries?: Record<string, string>;
  news_summary?: string;
  stats?: {
    total_papers: number;
    papers_by_category: Record<string, number>;
    total_news: number;
    news_by_category: Record<string, number>;
    top_keywords: string[];
  };
  generated_at?: string;
  // Legacy fields (optional/deprecated)
  all_papers?: AnalyzedPaper[];
  all_news?: AnalyzedNews[];
}

