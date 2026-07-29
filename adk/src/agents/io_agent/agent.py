from shared.agent_factory import create_se_agent
from shared.tools.design_date import current_date
from shared.tools.design_filesystem import (
    save_artifact,
    check_lock,
    release_lock,
    list_versions,
    promote_artifact,
    read_file,
    read_analysis_sections,
    read_multiple_files,
    list_design_files,
    clear_design_folder,
    check_active_blocks,
    append_artifact,
    patch_section,
    validate_analysis_sections,
    read_phase_manifest,
    read_phase_artifact,

)
from . import prompt

agent = create_se_agent(
    name="io_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        save_artifact,
        check_lock,
        release_lock,
        list_versions,
        promote_artifact,
        read_file,
        read_analysis_sections,
        read_multiple_files,
        current_date,
        list_design_files,
        clear_design_folder,
        check_active_blocks,
        append_artifact,
        patch_section,
        validate_analysis_sections,
        read_phase_manifest,
        read_phase_artifact,
    ],
    agent_subdir="io_agent",
)

root_agent = agent
