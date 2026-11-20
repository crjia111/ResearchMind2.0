"""Session-scoped AgentScope factory."""
from researchmind_skills.adapters.agentscope.factory import create_agent
def root_agent(runtime,context,model,**kwargs):
    return create_agent("database_agent",runtime,context,model,**kwargs)
