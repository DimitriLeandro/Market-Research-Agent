from ..schemas.research_schema import ResearchResult

class ReportRenderer:
    @staticmethod
    def render(result: ResearchResult) -> str:
        # Simple extraction from the Pydantic model
        # The 'summary_markdown' field from LLM does most of the heavy lifting,
        # but we wrap it with structured headers.
        
        icon = "🟢" if result.sentiment_score > 0 else "🔴" if result.sentiment_score < 0 else "⚪"
        
        md = f"# {result.ticker} Analysis {icon}\n"
        md += f"**Date:** {result.analysis_date}\n"
        md += f"**Sentiment:** {result.overall_sentiment.value} ({result.sentiment_score})\n"
        md += f"**Trend:** {result.price_trend.value}\n\n"
        
        md += "## 🚨 Key Events\n"
        for event in result.key_events:
            md += f"- **{event.event_name}** ({event.impact.value}): {event.description}\n"
            
        md += "\n## 📝 Detailed Summary\n"
        md += result.summary_markdown
        
        return md