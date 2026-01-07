"""Prompt templates for daily report generation."""

# =============================================================================
# Report Generation Prompts
# =============================================================================

REPORT_SYSTEM_PROMPT = """你是一位专业的 AI 技术分析师，负责撰写每日 AI 领域深度报告。
你的任务是基于提供的论文和新闻数据，生成高质量的领域总结。

<Tone>
专业、客观、深入。
避免使用营销话术或过于夸张的形容词。
</Tone>

<Language>
中文
</Language>
"""

# 1. 领域/分类总结 Prompt
CATEGORY_SUMMARY_USER_PROMPT = """请对以下 {category} 领域的论文进行总结。

<Papers>
{papers_content}
</Papers>

<Requirements>
1. 总结该领域今日的主要研究热点和趋势。
2. 提及具有代表性的论文（使用 [Title](ID) 格式引用）。
3. 归纳这些研究解决了什么核心问题，使用了什么新方法。
4. 篇幅控制在 200-300 字。
</Requirements>
"""

# 2. 新闻总结 Prompt
NEWS_SUMMARY_USER_PROMPT = """请对以下 AI 领域新闻进行总结。

<News>
{news_content}
</News>

<Requirements>
1. 总结今日 AI 行业的重大事件、产品发布和商业动态。
2. 将新闻按主题（如 LLM、基础设施、应用等）进行归类叙述。
3. 提及关键的公司或机构。
4. 篇幅控制在 200-300 字。
</Requirements>
"""

# 3. 日报总体总结 (Daily Summary) Prompt
DAILY_SUMMARY_USER_PROMPT = """请基于以下各个领域的详细总结，撰写一份今日 AI 领域日报的 Daily Summary。

<Category_Summaries>
{category_summaries_content}
</Category_Summaries>

<News_Summary>
{news_summary_content}
</News_Summary>

<Requirements>
1.这是一份 Executive Summary，供忙碌的专业人士快速阅读。
2. 宏观概括今日 AI 领域的整体风向（学术界 + 工业界）。
3. 突出最值得关注的 1-3 个核心亮点（Breakthroughs or Major Events）。
4. 融合不同领域的信息，发现潜在的跨领域联系。
5. 字数严格控制在 300-400 字。
6. 不要列出清单，写成连贯的文章段落。
</Requirements>
"""

