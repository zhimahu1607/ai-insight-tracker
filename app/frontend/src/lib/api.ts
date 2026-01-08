import type { AnalyzedPaper, AnalyzedNews, FileList, DailyReport } from "@/types";

const BASE_URL = import.meta.env.BASE_URL;

/**
 * 解析 JSONL 格式数据
 * 处理空行和解析错误
 */
function parseJSONL<T>(text: string): T[] {
  if (!text.trim()) return [];
  
  return text
    .trim()
    .split('\n')
    .filter(line => line.trim()) // 过滤空行
    .map((line, index) => {
      try {
        return JSON.parse(line) as T;
      } catch (e) {
        console.warn(`JSONL 第 ${index + 1} 行解析失败:`, e);
        return null;
      }
    })
    .filter((item): item is T => item !== null);
}

/**
 * 尝试解析响应数据（支持标准 JSON 数组和 JSONL）
 */
async function parseResponse<T>(res: Response): Promise<T[]> {
  const text = await res.text();
  
  // 1. 尝试解析为标准 JSON 数组
  try {
    const data = JSON.parse(text);
    if (Array.isArray(data)) {
      return data as T[];
    }
  } catch (e) {
    // 不是标准 JSON，继续尝试 JSONL
  }

  // 2. 尝试解析为 JSONL
  return parseJSONL<T>(text);
}

export async function getPapers(dateOrFilename: string): Promise<AnalyzedPaper[]> {
  // 优先尝试 .json，如果输入包含 .jsonl 则替换
  let filename = dateOrFilename;
  if (!filename.endsWith('.json') && !filename.endsWith('.jsonl')) {
    filename += '.json';
  } else if (filename.endsWith('.jsonl')) {
    filename = filename.replace('.jsonl', '.json');
  }

  let res = await fetch(`${BASE_URL}data/papers/${filename}`);
  
  // 如果 .json 不存在，尝试回退到 .jsonl (兼容旧数据)
  if (!res.ok && filename.endsWith('.json')) {
      const jsonlName = filename.replace('.json', '.jsonl');
      const resJsonl = await fetch(`${BASE_URL}data/papers/${jsonlName}`);
      if (resJsonl.ok) {
          res = resJsonl;
      }
  }

  if (!res.ok) {
    if (res.status === 404) return []; // 当天无数据
    throw new Error('Failed to fetch papers');
  }

  // 统一解析
  const papers = await parseResponse<AnalyzedPaper>(res);
  return papers.filter(p => p.analysis_status === 'success');
}

export async function getNews(dateOrFilename: string): Promise<AnalyzedNews[]> {
  // 优先尝试 .json，如果输入包含 .jsonl 则替换
  let filename = dateOrFilename;
  if (!filename.endsWith('.json') && !filename.endsWith('.jsonl')) {
    filename += '.json';
  } else if (filename.endsWith('.jsonl')) {
    filename = filename.replace('.jsonl', '.json');
  }

  let res = await fetch(`${BASE_URL}data/news/${filename}`);
  
  // 如果 .json 不存在，尝试回退到 .jsonl
  if (!res.ok && filename.endsWith('.json')) {
      const jsonlName = filename.replace('.json', '.jsonl');
      const resJsonl = await fetch(`${BASE_URL}data/news/${jsonlName}`);
      if (resJsonl.ok) {
          res = resJsonl;
      }
  }

  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error('Failed to fetch news');
  }

  const news = await parseResponse<AnalyzedNews>(res);
  return news.filter(n => n.analysis_status === 'success');
}

export async function getFileList(): Promise<FileList> {
  // 在开发环境中，如果没有生成 data 目录，可能会 404。
  // 生产环境中应由工作流生成 file-list.json
  try {
    const res = await fetch(`${BASE_URL}data/file-list.json`);
    if (!res.ok) {
         console.warn("Failed to fetch file list, using mock/empty data");
         return { papers: [], news: [], reports: [], last_updated: new Date().toISOString() };
    }
    return res.json();
  } catch (error) {
    console.warn("Error fetching file list:", error);
    return { papers: [], news: [], reports: [], last_updated: new Date().toISOString() };
  }
}

export async function getReport(dateOrFilename: string): Promise<DailyReport | null> {
  // 支持传入日期 (2025-12-30) 或完整文件名 (2025-12-30.json)
  const filename = dateOrFilename.endsWith('.json') ? dateOrFilename : `${dateOrFilename}.json`;
  try {
    const res = await fetch(`${BASE_URL}data/reports/${filename}`);
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error('Failed to fetch report');
    }
    return res.json();
  } catch (error) {
    console.warn("Error fetching report:", error);
    return null;
  }
}

