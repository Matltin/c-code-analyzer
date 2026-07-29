"""Multi-file project analysis and navigation APIs."""

from c_analyzer.project.analyzer import (
    ProjectAnalyzer,
    analyze_project,
    load_project_directory,
)
from c_analyzer.project.model import (
    DefinitionResult,
    ProjectAnalysis,
    ProjectFile,
    ProjectHover,
    ProjectLocation,
    ProjectReference,
    ProjectSymbol,
    normalize_project_path,
)
from c_analyzer.project.navigation import (
    find_references,
    goto_definition,
    hover_project,
    symbol_at,
)

__all__ = [
    "DefinitionResult",
    "ProjectAnalysis",
    "ProjectAnalyzer",
    "ProjectFile",
    "ProjectHover",
    "ProjectLocation",
    "ProjectReference",
    "ProjectSymbol",
    "analyze_project",
    "find_references",
    "goto_definition",
    "hover_project",
    "load_project_directory",
    "normalize_project_path",
    "symbol_at",
]
