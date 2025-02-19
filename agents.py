import os
import asyncio
import markdown
from data_scrapers import get_treasury_yield, assess_yield_curve, get_stock_quotes
from llama_index.llms.openai import OpenAI
from llama_index.core.workflow import Context
from tavily import AsyncTavilyClient
from dotenv import load_dotenv
from llama_index.core.agent.workflow import FunctionAgent, AgentWorkflow, AgentOutput, ToolCallResult, ToolCall

load_dotenv()

# Initialize LLM (Using OpenAI, but can be changed)
llm = OpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))


async def fetch_market_news(ctx: Context, query: str) -> str:
    """
    Fetch and summarize key market news.
    """
    client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    search_results = await client.search(query)

    # Summarizing News Before Returning
    summary_prompt = f"""
    Below is a list of recent news headlines and summaries:
    {search_results}

    Extract key **themes and trends** that will impact **interest rates, Treasury yields, and credit markets**.
    - Do not list individual headlines.
    - Focus on **macro-level** economic shifts.
    - Identify risks and potential opportunities for fixed-income traders.
    
    Respond with a **short 3-paragraph summary** of the key takeaways.
    """

    news_summary = llm.complete(summary_prompt).text
    
    # Store current state
    current_state = await ctx.get("state")
    current_state["research_notes"] = news_summary
    await ctx.set("state", current_state)
    
    print("🔀 Handoff from NewsAgent to ForecastAgent")  # Debugging

    return "News summary generated."


async def predict_market_trends(ctx: Context) -> str:
    """
    Analyze recent trends and provide a fixed-income forecast for traders.
    """
    current_state = await ctx.get("state")
    news_data = current_state.get("research_notes", '')

    if not news_data:
        print("❌ No research_notes found! Skipping ForecastAgent")
        return "No data available to generate forecast."
    
    # get 10-year treasury yield
    treasury_yield = get_treasury_yield()
    
    # assess yield curve
    spread, curve_status = assess_yield_curve()

    # fetch stock quotes desired in report
    stock_quotes = get_stock_quotes()
    sp = stock_quotes['S&P 500']['price']
    sp_change = stock_quotes['S&P 500']['change']
    sp_change_pct = stock_quotes['S&P 500']['change_pct']

    dow = stock_quotes['Dow Jones']['price']
    dow_change = stock_quotes['Dow Jones']['change']
    dow_change_pct = stock_quotes['Dow Jones']['change_pct']

    nasdaq = stock_quotes['Nasdaq']['price']
    nasdaq_change = stock_quotes['Nasdaq']['change']
    nasdaq_change_pct = stock_quotes['Nasdaq']['change_pct']

    # LLM prompt with real market data
    prompt = f"""
    You are a financial analyst specializing in macroeconomics, fixed income, and equity markets. 
    Analyze the following real-time market data and predict how these factors will influence short-term trends in both fixed-income and equity markets.

    ## 📉 Market Data:
    - **10-Year Treasury Yield**: {treasury_yield:.2f}%
    - **Yield Curve Status**: {curve_status} (Spread: {spread:.2f}%)

    ## 📈 Stock Market Performance:
    Below is a summary of major US indices, including daily changes in dollar amount and percentage:

    | Index         | Price   | Change ($) | Change (%) |
    |--------------|---------|-----------|-----------|
    | **S&P 500**  | {sp}  | {sp_change}  | {sp_change_pct}%  |
    | **Dow Jones**| {dow}  | {dow_change}  | {dow_change_pct}%  |
    | **Nasdaq**   | {nasdaq}  | {nasdaq_change}  | {nasdaq_change_pct}%  |

    ##  **Your Task:**
    ### **Fixed-Income Analysis**
    1️⃣ **Interest Rate Forecast:**  
    - Predict how the Fed's next decision might impact bond yields. Will they rise or fall?  
    - How will monetary policy affect short-term and long-term interest rates?  

    2️⃣ **Corporate Bond Spreads:**  
    - Will investors demand higher spreads on corporate debt?  
    - Which sectors are most at risk given the latest market developments?  

    3️⃣ **Fixed-Income Investment Strategy:**  
    - Should traders shift to short-duration bonds, long-term bonds, or inflation-protected securities (TIPS)?  
    - How should credit investors adjust their portfolio allocations?  

    ---

    ### **Equity Market Analysis**
    4️⃣ **Stock Market Trends:**  
    - Analyze the recent movement of the **S&P 500, Dow, and Nasdaq** based on market data.  
    - What trends are emerging across sectors (e.g., Tech, Financials, Industrials)?  

    5️⃣ **Market Volatility & Risk Sentiment:**  
    - Assess investor sentiment based on bond yields and stock performance.  
    - Is the market in a "risk-on" or "risk-off" mode?  

    6️⃣ **Equity Investment Strategy:**  
    - Should equity investors shift toward defensive stocks (e.g., utilities, healthcare) or growth sectors (e.g., tech, consumer discretionary)?  
    - How should traders position themselves in large-cap vs. small-cap equities?  

    ---

    ### 🔹 **Final Recommendation**
    7️⃣ **Cross-Market Strategy:**  
    - Given the current **bond and equity market conditions**, what is the best approach for institutional investors?  
    - Are there opportunities in **sector rotation**, **hedging**, or **alternative assets**?  
    
    Respond with a structured analysis and **clear, actionable strategies** for both fixed-income and equity market participants.
    """

    forecast = llm.complete(prompt).text
    print("✅ Forecast Generated:", forecast)  # Debugging

    current_state["market_forecast"] = forecast
    await ctx.set("state", current_state)
 
    print("🔀 Handoff from ForecastAgent to ReportAgent")  # Debugging

    return {"handoff_to": "ReportAgent", 
            "forecast": forecast
            }


async def format_report(ctx: Context, report_content: str) -> str:
    """
    Formats the report into a structured HTML document and saves it.
    """
    state = await ctx.get("state")

    research_notes = state.get("research_notes", "No research notes available.")
    market_forecast = state.get("market_forecast", "Market forecast not generated.")

    # Fetch stock quotes with latest prices, changes, and percentage changes
    stock_quotes = get_stock_quotes()

    # Function to format price changes with color coding
    def format_change(change, change_pct):
        if isinstance(change, str) or isinstance(change_pct, str):
            return f'N/A'
        elif change > 0:
            return f'<span style="color:green;">+{change} (+{change_pct}%)</span>'
        elif change < 0:
            return f'<span style="color:red;">{change} ({change_pct}%)</span>'
        else:
            return f'<span style="color:black;">{change} ({change_pct}%)</span>'

    # Construct HTML table for stock quotes (kept as pure HTML)
    stock_table = f"""
    <h2>📉 Stock Market Overview</h2>
    <table border="1" cellspacing="0" cellpadding="5" style="width:100%; text-align:center; border-collapse: collapse;">
        <tr style="background-color: #f4f4f4;">
            <th>Index</th>
            <th>Price</th>
            <th>Prev Close</th>
            <th>Change ($ & %)</th>
        </tr>
        <tr>
            <td><b>S&P 500</b></td>
            <td>{stock_quotes["S&P 500"]["price"]}</td>
            <td>{stock_quotes["S&P 500"]["prev_close"]}</td>
            <td>{format_change(stock_quotes["S&P 500"]["change"], stock_quotes["S&P 500"]["change_pct"])}</td>
        </tr>
        <tr>
            <td><b>Dow Jones</b></td>
            <td>{stock_quotes["Dow Jones"]["price"]}</td>
            <td>{stock_quotes["Dow Jones"]["prev_close"]}</td>
            <td>{format_change(stock_quotes["Dow Jones"]["change"], stock_quotes["Dow Jones"]["change_pct"])}</td>
        </tr>
        <tr>
            <td><b>Nasdaq</b></td>
            <td>{stock_quotes["Nasdaq"]["price"]}</td>
            <td>{stock_quotes["Nasdaq"]["prev_close"]}</td>
            <td>{format_change(stock_quotes["Nasdaq"]["change"], stock_quotes["Nasdaq"]["change_pct"])}</td>
        </tr>
    </table>
    """

    # generate markdown content ** without including the table in markdown conversion **
    markdown_content = f"""
# 📊 US Equity & Fixed Income Market Report

## 📰 Key Market News  
{research_notes}

{market_forecast}
  
"""

    # Convert Markdown to HTML for non-table content
    html_content = markdown.markdown(markdown_content, extensions=["extra"])

    # Combine Markdown-rendered HTML **with the raw HTML stock table**  
    final_html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Market Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: auto; padding: 20px; }}
            h1, h2, h3 {{ color: #333; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
            p, li {{ color: #555; }}
            ul {{ padding-left: 25px; list-style-type: disc; }}  /* Circular bullets */
            strong {{ font-weight: bold; }}
            hr {{ margin: 20px 0; border: 0; border-top: 1px solid #ccc; }}
            .footer {{ text-align: center; font-size: 0.8em; margin-top: 30px; color: #777; }}
            table {{ width: 100%; border-collapse: collapse; text-align: center; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            th {{ background-color: #f4f4f4; }}
        </style>
    </head>
    <body>
        <div>{html_content}</div>
        {stock_table}  <!-- Inject HTML table here -->
        <p class="footer"><strong>Generated by AI Research Agents</strong></p>
    </body>
    </html>"""

    report_path = os.getenv("REPORT_PATH")
    if not report_path:
        print("❌ ERROR: REPORT_PATH not set in .env file!")
        return "Failed to save report. REPORT_PATH missing."

    # Normalize Windows-style paths
    report_path = os.path.normpath(report_path)

    try:
        # Save the properly formatted HTML file
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(final_html)

        state["final_report"] = final_html
        await ctx.set("state", state)

        print(f"✅ Report successfully saved at: {report_path}")
        return "Report formatted successfully."

    except Exception as e:
        print(f"❌ ERROR: Could not save report - {e}")
        return f"Failed to save report: {e}"



news_agent = FunctionAgent(
    name="NewsAgent",
    description="Fetches recent news about the US equity market.",
    system_prompt="Fetch the latest news related to US stock markets and significant financial trends. Give some specific news around treasury data.",
    llm=llm,
    tools=[fetch_market_news],
    can_handoff_to=["ForecastAgent"]
)

forecast_agent = FunctionAgent(
    name="ForecastAgent",
    description="Analyzes news data and generates a near-term market forecast.",
    system_prompt="Use recent news to predict the short-term trends in the stock market. Provide numerical details that could be useful to bank fixed income traders",
    llm=llm,
    tools=[predict_market_trends],
    can_handoff_to=["ReportAgent"]
)

report_agent = FunctionAgent(
    name="ReportAgent",
    description="Formats and exports the final report.",
    system_prompt="Format the final market analysis report into Markdown.",
    llm=llm,
    tools=[format_report],
    can_handoff_to=[]
)

agent_workflow = AgentWorkflow(
    agents=[news_agent, forecast_agent, report_agent],
    root_agent=news_agent.name,
    initial_state={
        "research_notes": "",
        "market_forecast": "Not generated yet.",
        "final_report": "Not written yet.",
    }
)


async def main():
    handler = agent_workflow.run(
        user_msg="Fetch the latest US equity and treasury market news and generate a forecast report including current day quotes for the DOW, S and P 500, and NASDAQ."
    )
    await process_events(handler)


async def process_events(handler):
    current_agent = None
    
    async for event in handler.stream_events():
        if (
            hasattr(event, "current_agent_name")
            and event.current_agent_name != current_agent
        ):
            current_agent = event.current_agent_name
            print(f"\n{'='*50}")
            print(f"🤖 Agent: {current_agent} is now active")
            print(f"{'='*50}\n")

        if isinstance(event, AgentOutput):
            if event.response.content:
                print("📤 Output:", event.response.content)
            if event.tool_calls:
                print(
                    "🛠️  Planning to use tools:",
                    [call.tool_name for call in event.tool_calls],
                )

        elif isinstance(event, ToolCallResult):
            print(f"🔧 Tool Result ({event.tool_name}):")
            print(f"  Arguments: {event.tool_kwargs}")
            print(f"  Output: {event.tool_output}")

        elif isinstance(event, ToolCall):
            print(f"🔨 Calling Tool: {event.tool_name}")
            print(f"  With arguments: {event.tool_kwargs}")

        # ✅ **Track handoff attempts explicitly**
        elif hasattr(event, "handoff_to_agent"):
            print(f"🚀 Handoff triggered to: {event.handoff_to_agent}")


if __name__ == "__main__":
    asyncio.run(main())