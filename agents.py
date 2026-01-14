from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
import operator

load_dotenv()

# Initialize Groq LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

# Initialize DuckDuckGo Search (FREE - No API key needed!)
search_tool = DuckDuckGoSearchResults(max_results=5)


# Define State Schema
class ResearchState(TypedDict):
    code_snippet: str
    error_message: str
    search_queries: List[str]
    search_results: List[str]
    source_urls: List[str]
    analysis: str
    solution: str
    quality_score: int
    iteration_count: int
    messages: Annotated[List[str], operator.add]


# Agent 1: Research Agent
def research_agent(state: ResearchState) -> ResearchState:
    """Searches web for error solutions"""
    print("\n🔍 Research Agent: Searching for solutions...")
    
    code = state["code_snippet"]
    error = state["error_message"]
    
    # Generate search queries
    query_prompt = f"""Given this error, generate 2-3 specific search queries to find solutions:
    
Error: {error[:500]}

Return ONLY the search queries, one per line, no numbering or extra text."""
    
    response = llm.invoke([HumanMessage(content=query_prompt)])
    queries = [q.strip() for q in response.content.strip().split('\n') if q.strip()]
    
    # Perform searches and extract URLs
    all_results = []
    all_urls = []
    
    for query in queries[:2]:  # Limit to 2 queries for speed
        try:
            results = search_tool.invoke(query)
            all_results.append(f"Query: {query}\nResults: {results}\n")
            
            # Extract URLs from results (DuckDuckGo returns snippets with links)
            import re
            urls = re.findall(r'link: (https?://[^\s,\]]+)', str(results))
            all_urls.extend(urls[:3])  # Get top 3 URLs per query
            
        except Exception as e:
            all_results.append(f"Query: {query}\nError searching: {str(e)}\n")
    
    state["search_queries"] = queries
    state["search_results"] = all_results
    state["source_urls"] = list(set(all_urls))  # Remove duplicates
    state["messages"] = [f"Searched {len(queries)} queries, found {len(all_urls)} sources"]
    
    return state


# Agent 2: Synthesis Agent
def synthesis_agent(state: ResearchState) -> ResearchState:
    """Analyzes results and creates solution"""
    print("\n📝 Synthesis Agent: Creating solution...")
    
    synthesis_prompt = f"""You are an expert technical troubleshooter. Analyze the error and provide a clear, actionable solution.

ERROR/ISSUE:
{state['error_message']}

CONTEXT (if any):
{state['code_snippet']}

SEARCH RESULTS:
{' '.join(state['search_results'][:1500])}

SOURCE URLS FOUND:
{', '.join(state.get('source_urls', [])[:5])}

Provide a comprehensive solution in this EXACT format:

**Root Cause:**
[Explain what's causing the error in 2-3 sentences]

**Solution:**
[Step-by-step fix with specific commands/code]

**Prevention:**
[How to avoid this in future]

**Sources Referenced:**
[List the most relevant source URLs that helped solve this]

Be specific, actionable, and technical. Include exact commands, file paths, and code snippets."""
    
    response = llm.invoke([
        SystemMessage(content="You are an expert technical troubleshooter specializing in installation errors, dependency conflicts, and system issues."),
        HumanMessage(content=synthesis_prompt)
    ])
    
    state["solution"] = response.content
    state["messages"] = [f"Generated solution ({len(response.content)} chars)"]
    
    return state


# Agent 3: Quality Agent (Self-Correction)
def quality_agent(state: ResearchState) -> ResearchState:
    """Evaluates solution quality and decides if re-research is needed"""
    print("\n✅ Quality Agent: Evaluating solution...")
    
    quality_prompt = f"""Rate this solution's quality on a scale of 1-10:

ERROR: {state['error_message']}
SOLUTION: {state['solution'][:500]}

Consider:
- Does it address the specific error?
- Is it actionable and clear?
- Does it provide code examples?

Return ONLY a number from 1-10."""
    
    response = llm.invoke([HumanMessage(content=quality_prompt)])
    
    try:
        score = int(response.content.strip().split()[0])
    except:
        score = 7  # Default to acceptable
    
    state["quality_score"] = score
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    state["messages"] = [f"Quality score: {score}/10"]
    
    return state


# Conditional Edge: Decide if we need to re-research
def should_continue(state: ResearchState) -> str:
    """Cyclic state management - decides next step"""
    score = state["quality_score"]
    iteration = state.get("iteration_count", 0)
    
    # If quality is good OR we've tried twice, end
    if score >= 7 or iteration >= 2:
        print(f"\n✅ Quality acceptable ({score}/10) or max iterations reached. Finishing...")
        return "end"
    else:
        print(f"\n🔄 Quality low ({score}/10). Re-researching...")
        return "re_research"


# Build LangGraph Workflow
def create_research_workflow():
    """Creates the multi-agent workflow with cyclic self-correction"""
    
    workflow = StateGraph(ResearchState)
    
    # Add nodes (agents)
    workflow.add_node("research", research_agent)
    workflow.add_node("synthesis", synthesis_agent)
    workflow.add_node("quality", quality_agent)
    
    # Define edges (flow)
    workflow.set_entry_point("research")
    workflow.add_edge("research", "synthesis")
    workflow.add_edge("synthesis", "quality")
    
    # Conditional edge for self-correction (CYCLIC!)
    workflow.add_conditional_edges(
        "quality",
        should_continue,
        {
            "end": END,
            "re_research": "research"  # Loop back!
        }
    )
    
    return workflow.compile()


# Main execution function
def research_code_error(code_snippet: str, error_message: str) -> dict:
    """
    Main entry point for code error research
    
    Args:
        code_snippet: The problematic code
        error_message: The error message received
    
    Returns:
        dict with solution and metadata
    """
    
    initial_state = {
        "code_snippet": code_snippet,
        "error_message": error_message,
        "search_queries": [],
        "search_results": [],
        "source_urls": [],
        "analysis": "",
        "solution": "",
        "quality_score": 0,
        "iteration_count": 0,
        "messages": []
    }
    
    # Create and run workflow
    app = create_research_workflow()
    
    print("\n" + "="*60)
    print("🚀 Starting Multi-Agent Research Workflow...")
    print("="*60)
    
    # Execute the workflow
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*60)
    print("✅ Research Complete!")
    print("="*60)
    
    return {
        "solution": final_state["solution"],
        "quality_score": final_state["quality_score"],
        "iterations": final_state["iteration_count"],
        "search_queries": final_state["search_queries"],
        "source_urls": final_state.get("source_urls", [])
    }


# Test function
if __name__ == "__main__":
    # Example usage
    test_code = """
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

result = calculate_average([])
print(result)
    """
    
    test_error = "ZeroDivisionError: division by zero"
    
    result = research_code_error(test_code, test_error)
    
    print("\n" + "="*60)
    print("FINAL SOLUTION:")
    print("="*60)
    print(result["solution"])
    print(f"\n📊 Quality: {result['quality_score']}/10")
    print(f"🔄 Iterations: {result['iterations']}")