import type { AnalyzedNews, AnalyzedPaper, DailyReport, FileList } from "@/types";

const BASE_URL = import.meta.env.BASE_URL;

function parseJSONL<T>(text: string): T[] {
  if (!text.trim()) return [];

  return text
    .trim()
    .split("\n")
    .filter((line) => line.trim())
    .map((line, index) => {
      try {
        return JSON.parse(line) as T;
      } catch (error) {
        console.warn(`Failed to parse JSONL line ${index + 1}:`, error);
        return null;
      }
    })
    .filter((item): item is T => item !== null);
}

async function parseResponse<T>(res: Response): Promise<T[]> {
  const text = await res.text();

  try {
    const data = JSON.parse(text);
    if (Array.isArray(data)) return data as T[];
  } catch {
    // Fall back to JSONL.
  }

  return parseJSONL<T>(text);
}

function dataFilename(dateOrFilename: string): string {
  if (!dateOrFilename.endsWith(".json") && !dateOrFilename.endsWith(".jsonl")) {
    return `${dateOrFilename}.json`;
  }
  return dateOrFilename.endsWith(".jsonl")
    ? dateOrFilename.replace(".jsonl", ".json")
    : dateOrFilename;
}

async function fetchDataList<T extends { analysis_status?: string }>(
  folder: "papers" | "news",
  dateOrFilename: string,
): Promise<T[]> {
  const filename = dataFilename(dateOrFilename);
  let res = await fetch(`${BASE_URL}data/${folder}/${filename}`);

  if (!res.ok && filename.endsWith(".json")) {
    const fallback = filename.replace(".json", ".jsonl");
    const fallbackRes = await fetch(`${BASE_URL}data/${folder}/${fallback}`);
    if (fallbackRes.ok) res = fallbackRes;
  }

  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error(`Failed to fetch ${folder}`);
  }

  const items = await parseResponse<T>(res);
  return items.filter((item) => item.analysis_status === "success");
}

export async function getPapers(dateOrFilename: string): Promise<AnalyzedPaper[]> {
  return fetchDataList<AnalyzedPaper>("papers", dateOrFilename);
}

export async function getNews(dateOrFilename: string): Promise<AnalyzedNews[]> {
  return fetchDataList<AnalyzedNews>("news", dateOrFilename);
}

export async function getFileList(): Promise<FileList> {
  try {
    const res = await fetch(`${BASE_URL}data/file-list.json`);
    if (!res.ok) {
      console.warn("Failed to fetch file list, using empty data");
      return { papers: [], news: [], reports: [], last_updated: new Date().toISOString() };
    }
    return res.json();
  } catch (error) {
    console.warn("Error fetching file list:", error);
    return { papers: [], news: [], reports: [], last_updated: new Date().toISOString() };
  }
}

export async function getReport(dateOrFilename: string): Promise<DailyReport | null> {
  const filename = dateOrFilename.endsWith(".json") ? dateOrFilename : `${dateOrFilename}.json`;
  try {
    const res = await fetch(`${BASE_URL}data/reports/${filename}`);
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error("Failed to fetch report");
    }
    return res.json();
  } catch (error) {
    console.warn("Error fetching report:", error);
    return null;
  }
}
