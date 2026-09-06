"""GLSL preprocessing ported from lordmauve/riverborn (e73a393)."""
from pathlib import Path
import re
import os
from typing import Dict, List, Tuple, Set, Optional, Any



# Location information for a line of code
SourceLoc = Tuple[str, int, str]  # (filename, line_number, line_content)

shaders = Path(__file__).parent / 'glsl' / 'include'


def preprocess_shader(
    source: str,
    defines: Optional[Dict[str, str]] = None,
    include_dirs: Optional[List[Any]] = None,
    processed_includes: Optional[Set[str]] = None,
    source_filename: str = "<string>",
) -> Tuple[str, List[SourceLoc]]:
    """Preprocess a shader source adding support for simple #include and #ifdef directives.

    Args:
        source: The shader source code to preprocess
        defines: Dictionary of define names and their values
        include_dirs: List of directories to search for include files
        processed_includes: Internal use only - set of already processed include files to avoid circularity
        source_filename: Name of the source file (for error reporting)

    Returns:
        Preprocessed shader source and source location mapping
    """
    defines = {} if defines is None else defines
    include_dirs = include_dirs or [shaders]
    processed_includes = set() if processed_includes is None else processed_includes

    # Split source into lines and track source locations
    source_lines = source.splitlines()
    source_locs: List[SourceLoc] = []
    for i, line in enumerate(source_lines):
        source_locs.append((source_filename, i + 1, line))

    if not source_lines:
        return "", []

    # Process #include directives recursively
    i = 0
    result_lines = []
    result_locs = []

    while i < len(source_lines):
        line = source_lines[i]
        loc = source_locs[i]

        # Handle include directive
        include_match = re.match(r'^\s*#include\s+([<"].*?[>"])', line)
        if include_match:
            filename = include_match.group(1).strip('"').strip('<>')

            # Avoid circular includes
            if filename in processed_includes:
                result_lines.append(f"// Already included: {filename}")
                result_locs.append((loc[0], loc[1], f"// Already included: {filename}"))
                i += 1
                continue

            # Find and process the include file
            included_content = None
            included_file_path = None

            for dir_path in include_dirs:
                try:
                    if isinstance(dir_path, str):
                        filepath = os.path.join(dir_path, filename)
                        if os.path.exists(filepath):
                            with open(filepath, 'r') as f:
                                included_content = f.read()
                                included_file_path = os.path.abspath(filepath)
                                break
                    else:
                        # Handle Path-like objects from importlib.resources
                        include_path = dir_path / filename
                        if include_path.exists():
                            included_content = include_path.read_text()
                            included_file_path = str(include_path)
                            break
                except (FileNotFoundError, IsADirectoryError):
                    continue

            if included_content is None:
                raise FileNotFoundError(f"Could not find include file {filename}")

            # Add to processed includes to avoid circularity
            processed_includes.add(filename)

            inner_processed, inner_locs = preprocess_shader(
                included_content, defines, include_dirs,
                processed_includes, included_file_path,
            )

            # Add processed content to result
            inner_lines = inner_processed.splitlines()
            result_lines.extend(inner_lines)
            result_locs.extend(inner_locs)

            i += 1
            continue

        # Handle #ifdef
        ifdef_match = re.match(r'^\s*#ifdef\s+(\w+)\s*$', line)
        if ifdef_match:
            define_name = ifdef_match.group(1)
            is_defined = define_name in defines

            # Skip to matching #else or #endif
            end, lines_to_add, locs_to_add = process_conditional_block(
                source_lines, source_locs, i, defines, is_defined)

            source_lines[i:end] = lines_to_add
            source_locs[i:end] = locs_to_add
            continue

        # Handle #ifndef
        ifndef_match = re.match(r'^\s*#ifndef\s+(\w+)\s*$', line)
        if ifndef_match:
            define_name = ifndef_match.group(1)
            is_not_defined = define_name not in defines

            # Skip to matching #else or #endif
            end, lines_to_add, locs_to_add = process_conditional_block(
                source_lines, source_locs, i, defines, is_not_defined)

            source_lines[i:end] = lines_to_add
            source_locs[i:end] = locs_to_add
            continue

        # Handle #else without matching #ifdef/#ifndef
        else_match = re.match(r'^\s*#else\s*$', line)
        if else_match:
            raise SyntaxError("#else without matching #ifdef/#ifndef")

        # Handle #endif without matching #ifdef/#ifndef
        endif_match = re.match(r'^\s*#endif\s*$', line)
        if endif_match:
            raise SyntaxError("#endif without matching #ifdef/#ifndef")

        # Handle #define - keep the definition in the output
        define_match = re.match(r'^\s*#define\s+(\w+)(?:\s+(.*))?$', line)
        if define_match:
            define_name = define_match.group(1)
            define_value = define_match.group(2) or "1"
            defines[define_name] = define_value.strip()

            result_lines.append(line)
            result_locs.append(loc)
            i += 1
            continue

        # Add regular line to the result
        result_lines.append(line)
        result_locs.append(loc)
        i += 1

    processed_source = '\n'.join(result_lines)
    if result_lines and result_lines[-1] == '':
        processed_source += '\n'
    return processed_source, result_locs


def process_conditional_block(
    source_lines,
    source_locs,
    start_idx,
    defines,
    condition_result
) -> Tuple[int, List[str], List[SourceLoc]]:
    """Process a conditional block (#ifdef/#ifndef) and return the result.

    Args:
        source_lines: List of source lines
        source_locs: List of source locations
        start_idx: Index of the #ifdef/#ifndef line
        defines: Dictionary of preprocessor defines
        condition_result: Result of the condition (True/False)

    Returns:
        Tuple of (new_idx, lines_to_add, locs_to_add)
    """
    i = start_idx + 1  # Skip the opening directive
    nesting_level = 1
    lines_if_branch = []
    locs_if_branch = []
    lines_else_branch = []
    locs_else_branch = []

    in_else_branch = False

    while i < len(source_lines) and nesting_level > 0:
        line = source_lines[i]
        loc = source_locs[i]

        # Check for nested directives
        if re.match(r'^\s*#ifdef\s+\w+\s*$', line) or re.match(r'^\s*#ifndef\s+\w+\s*$', line):
            nesting_level += 1
            # For nested directives, we need to include the directive line in the output
            # for the chosen branch
            if not in_else_branch and condition_result:
                lines_if_branch.append(line)
                locs_if_branch.append(loc)
            elif in_else_branch and not condition_result:
                lines_else_branch.append(line)
                locs_else_branch.append(loc)
        elif re.match(r'^\s*#endif\s*$', line):
            nesting_level -= 1
            if nesting_level == 0:
                # End of this conditional block - don't include the #endif
                i += 1
                break
            # For nested directives, include the #endif in the output
            # for the chosen branch
            if not in_else_branch and condition_result:
                lines_if_branch.append(line)
                locs_if_branch.append(loc)
            elif in_else_branch and not condition_result:
                lines_else_branch.append(line)
                locs_else_branch.append(loc)
        elif nesting_level == 1 and re.match(r'^\s*#else\s*$', line):
            in_else_branch = True
        else:
            # Add line to appropriate branch
            if not in_else_branch:
                if condition_result:
                    lines_if_branch.append(line)
                    locs_if_branch.append(loc)
            else:
                if not condition_result:
                    lines_else_branch.append(line)
                    locs_else_branch.append(loc)

        i += 1

    if nesting_level > 0:
        raise SyntaxError("Unclosed #ifdef or #ifndef directive")

    # Return the appropriate branch based on condition result
    if condition_result:
        return i, lines_if_branch, locs_if_branch
    else:
        return i, lines_else_branch, locs_else_branch


def format_shader_with_line_info(source: str, source_locs: List[SourceLoc]) -> str:
    """Format shader source with line information for error reporting."""
    lines = source.splitlines()
    annotated_lines = []

    source_locs = [f'{filename}:{lineno}' for filename, lineno, _ in source_locs]
    max_loc_length = max((len(loc) for loc in source_locs), default=0)

    for lineno, (loc, line) in enumerate(zip(source_locs, lines), start=1):

        annotated_lines.append(f"\x1b[36m{lineno:<4}\x1b[0m \x1b[2m{loc:<{max_loc_length}}\x1b[0m {line}")

    return '\n'.join(annotated_lines)

