"""
测试深度分析（含论文全文分析）
"""

import asyncio
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

async def main():
    from src.agents.paper.deep_analyzer import run_deep_analysis
    
    # 选择一篇论文进行深度分析
    paper_id = "2512.25052"
    paper_title = "AdaGReS:Adaptive Greedy Context Selection via Redundancy-Aware Scoring for Token-Budgeted RAG"
    paper_abstract = """Retrieval-augmented generation (RAG) is highly sensitive to the quality of selected context, yet standard top-k retrieval often returns redundant or near-duplicate chunks that waste token budget and degrade downstream generation. We present AdaGReS, a redundancy-aware context selection framework for token-budgeted RAG that optimizes a set-level objective combining query-chunk relevance and intra-set redundancy penalties. AdaGReS performs greedy selection under a token-budget constraint using marginal gains derived from the objective, and introduces a closed-form, instance-adaptive calibration of the relevance-redundancy trade-off parameter to eliminate manual tuning and adapt to candidate-pool statistics and budget limits. We further provide a theoretical analysis showing that the proposed objective exhibits epsilon-approximate submodularity under practical embedding similarity conditions, yielding near-optimality guarantees for greedy selection. Experiments on open-domain question answering (Natural Questions) and a high-redundancy biomedical (drug) corpus demonstrate consistent improvements in redundancy control and context quality, translating to better end-to-end answer quality and robustness across settings."""
    paper_pdf_url = "https://arxiv.org/pdf/2512.25052.pdf"
    
    print(f"开始深度分析: {paper_id}")
    print(f"论文标题: {paper_title}")
    print("=" * 80)
    
    try:
        result = await run_deep_analysis(
            paper_id=paper_id,
            paper_title=paper_title,
            paper_abstract=paper_abstract,
            paper_pdf_url=paper_pdf_url,
            requirements="请重点分析该方法的核心创新点、与现有 RAG 方法的对比优势、以及实际应用场景",
            enable_full_text=True,  # 启用全文分析
        )
        
        print("\n" + "=" * 80)
        print("深度分析完成！")
        print("=" * 80)
        print(f"论文 ID: {result.paper_id}")
        print(f"研究迭代次数: {result.research_iterations}")
        print(f"写作迭代次数: {result.write_iterations}")
        print(f"分析耗时: {result.analysis_duration_seconds:.1f} 秒")
        print(f"全文分析状态: {result.pdf_parse_status}")
        print(f"论文页数: {result.paper_total_pages}")
        print("\n" + "=" * 80)
        print("分析报告:")
        print("=" * 80)
        print(result.report)
        
    except Exception as e:
        logging.exception(f"深度分析失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

