from google.adk.tools import skill_toolset


def build_skill_toolset(skills: list) -> skill_toolset.SkillToolset:
    """Monta um SkillToolset a partir da lista de skills recebida."""
    return skill_toolset.SkillToolset(skills=skills)
