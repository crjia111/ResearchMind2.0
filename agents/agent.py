"""ResearchMind coordinator factory; Agent instances belong to a session."""
from researchmind_skills.adapters.agentscope.factory import create_agent
def research_coordinator(runtime,context,model,**kwargs):
    return create_agent("research_coordinator",runtime,context,model,**kwargs)
root_agent=research_coordinator
