"""Tests for the shader preprocessor functionality."""
import pytest
from pathlib import Path
import tempfile
import os

from wasabi2d.shader_preprocessor import preprocess_shader, format_shader_with_line_info, SourceLoc


def test_preprocess_empty_source():
    """Test preprocessor with empty source."""
    result = preprocess_shader("")
    processed, source_locs = result
    assert processed == ""
    assert len(source_locs) == 0


def create_include_file(temp_dir, filename, content):
    """Helper to create a temporary include file."""
    include_path = Path(temp_dir) / filename
    with open(include_path, "w") as f:
        f.write(content)
    return include_path


def test_include_directive():
    """Test that #include directives are processed correctly."""
    # Create temporary include files
    with tempfile.TemporaryDirectory() as temp_dir:
        include_content = "vec3 included_function() { return vec3(1.0, 2.0, 3.0); }"
        include_path = create_include_file(temp_dir, "test_include.glsl", include_content)

        # Test source with include
        source = "#version 330\n#include \"test_include.glsl\"\nvoid main() {}"
        result = preprocess_shader(source, include_dirs=[temp_dir])
        processed, source_locs = result

        # Expected output after preprocessing
        expected = "#version 330\nvec3 included_function() { return vec3(1.0, 2.0, 3.0); }\nvoid main() {}"
        assert processed == expected

        # Verify source mapping
        assert len(source_locs) == 3  # 3 lines in the processed output
        assert source_locs[0][0] == "<string>"  # First line from original source
        assert str(include_path) in source_locs[1][0]  # Second line from include file
        assert source_locs[2][0] == "<string>"  # Third line from original source


def test_source_mapping_basic():
    """Test that source mapping is correctly generated for basic input."""
    source = "line1\nline2\nline3"
    result = preprocess_shader(source, source_filename="test.glsl")
    processed, source_locs = result

    assert processed == source
    assert len(source_locs) == 3

    for i, loc in enumerate(source_locs):
        filename, lineno, content = loc
        assert filename == "test.glsl"
        assert lineno == i + 1
        assert content == f"line{i+1}"


@pytest.mark.parametrize(
    "source,defines,expected",
    [
        # IFDEF tests
        (
            """#version 330
#ifdef FEATURE_ENABLED
float feature() { return 1.0; }
#else
float feature() { return 0.0; }
#endif
void main() {}""",
            {"FEATURE_ENABLED": "1"},
            "#version 330\nfloat feature() { return 1.0; }\nvoid main() {}"
        ),
        (
            """#version 330
#ifdef FEATURE_ENABLED
float feature() { return 1.0; }
#else
float feature() { return 0.0; }
#endif
void main() {}""",
            {},
            "#version 330\nfloat feature() { return 0.0; }\nvoid main() {}"
        ),

        # IFNDEF tests
        (
            """#version 330
#ifndef FEATURE_DISABLED
float feature() { return 1.0; }
#else
float feature() { return 0.0; }
#endif
void main() {}""",
            {},
            "#version 330\nfloat feature() { return 1.0; }\nvoid main() {}"
        ),
        (
            """#version 330
#ifndef FEATURE_DISABLED
float feature() { return 1.0; }
#else
float feature() { return 0.0; }
#endif
void main() {}""",
            {"FEATURE_DISABLED": "1"},
            "#version 330\nfloat feature() { return 0.0; }\nvoid main() {}"
        ),
    ],
    ids=["ifdef-defined", "ifdef-not-defined", "ifndef-not-defined", "ifndef-defined"]
)
def test_conditional_directives(source, defines, expected):
    """Test conditional preprocessing directives."""
    result = preprocess_shader(source, defines=defines)
    processed, source_locs = result

    assert processed == expected

    # Verify source mapping - lines should map back to original source
    for loc in source_locs:
        assert loc[0] == "<string>"  # Default source filename


@pytest.mark.parametrize(
    "defines,expected_result",
    [
        (
            {"OUTER": "1", "INNER": "1"},
            "#version 330\n    float feature() { return 3.0; }\nvoid main() {}"
        ),
        (
            {"OUTER": "1"},
            "#version 330\n    float feature() { return 2.0; }\nvoid main() {}"
        ),
        (
            {"INNER": "1"},
            "#version 330\n    float feature() { return 1.0; }\nvoid main() {}"
        ),
        (
            {},
            "#version 330\n    float feature() { return 0.0; }\nvoid main() {}"
        ),
    ],
    ids=["outer-inner", "outer-only", "inner-only", "none"]
)
def test_nested_conditionals(defines, expected_result):
    """Test that nested #ifdef/#ifndef directives are processed correctly."""
    source = """#version 330
#ifdef OUTER
    #ifdef INNER
    float feature() { return 3.0; }
    #else
    float feature() { return 2.0; }
    #endif
#else
    #ifdef INNER
    float feature() { return 1.0; }
    #else
    float feature() { return 0.0; }
    #endif
#endif
void main() {}"""
    result = preprocess_shader(source, defines=defines)
    processed, source_locs = result

    assert processed == expected_result

    # Version, selected branch, and main retain their source locations.
    assert len(source_locs) == 3


def test_define_directive():
    """Test that #define directives are processed correctly."""
    source = """#version 330
#define MY_VALUE 42
#ifdef MY_VALUE
float getValue() { return MY_VALUE; }
#else
float getValue() { return 0.0; }
#endif
void main() {}"""
    result = preprocess_shader(source)
    processed, source_locs = result

    expected = """#version 330
#define MY_VALUE 42
float getValue() { return MY_VALUE; }
void main() {}"""
    assert processed == expected

    # Verify source mapping
    assert len(source_locs) == 4  # 4 lines in the processed output
    assert source_locs[0][1] == 1  # Line 1 in original source
    assert source_locs[1][1] == 2  # Line 2 in original source
    assert source_locs[2][1] == 4  # Line 4 in original source (from true branch)
    assert source_locs[3][1] == 8  # Line 8 in original source


@pytest.mark.parametrize(
    "source,expected_error",
    [
        (
            """#version 330
#ifdef FEATURE
float feature() { return 1.0; }
// Missing #endif
void main() {}""",
            "Unclosed #ifdef or #ifndef directive"
        ),
        (
            """#version 330
#else
float feature() { return 0.0; }
#endif
void main() {}""",
            "#else without matching #ifdef/#ifndef"
        ),
        (
            """#version 330
#endif
void main() {}""",
            "#endif without matching #ifdef/#ifndef"
        ),
    ],
    ids=["missing-endif", "else-without-ifdef", "endif-without-ifdef"]
)
def test_syntax_errors(source, expected_error):
    """Test that various syntax errors raise the expected exceptions."""
    with pytest.raises(SyntaxError) as excinfo:
        preprocess_shader(source)
    assert expected_error in str(excinfo.value)


def test_multiline_define():
    """Test multiline #define directive."""
    source = """#version 330
#define MULTILINE_FUNC(x) \\
    x * x + \\
    2 * x + 1
void main() {
    float value = MULTILINE_FUNC(5.0);
}"""
    result = preprocess_shader(source)
    processed, source_locs = result

    assert processed == source  # Should preserve multiline define directive
    assert len(source_locs) == 7  # 7 lines in total (includes closing brace)


def test_include_recursive():
    """Test inclusion of files that themselves have includes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a nested include structure
        inner_content = "float inner_func() { return 1.0; }"
        outer_content = "#include \"inner.glsl\"\nfloat outer_func() { return 2.0; }"

        inner_path = create_include_file(temp_dir, "inner.glsl", inner_content)
        outer_path = create_include_file(temp_dir, "outer.glsl", outer_content)

        # Test source with nested includes
        source = "#version 330\n#include \"outer.glsl\"\nvoid main() {}"
        result = preprocess_shader(source, include_dirs=[temp_dir])
        processed, source_locs = result

        expected = "#version 330\nfloat inner_func() { return 1.0; }\nfloat outer_func() { return 2.0; }\nvoid main() {}"
        assert processed == expected

        # Check source mapping
        assert len(source_locs) == 4
        assert source_locs[0][0] == "<string>"  # First line from original source
        assert str(inner_path) in source_locs[1][0]  # From inner.glsl
        assert str(outer_path) in source_locs[2][0]  # From outer.glsl
        assert source_locs[3][0] == "<string>"  # Last line from original source


def test_shadow_common_include():
    """Test the shadow_common.glsl include file directly."""
    # Create a simplified version of shadow_common.glsl
    shadow_common_content = """// Shadow mapping parameters
uniform sampler2D shadow_map;
uniform mat4 light_space_matrix;
uniform float shadow_bias;

float calculate_shadow(vec4 light_space_pos, float bias) {
    // Shadow calculation logic
    return 0.0;
}"""

    with tempfile.TemporaryDirectory() as temp_dir:
        shadow_path = create_include_file(temp_dir, "shadow_common.glsl", shadow_common_content)

        # Test source with include
        source = "#version 330\n#include \"shadow_common.glsl\"\nvoid main() {}"
        result = preprocess_shader(source, include_dirs=[temp_dir])
        processed, source_locs = result

        expected = "#version 330\n" + shadow_common_content + "\nvoid main() {}"
        assert processed == expected

        # Check source mapping for included content
        assert source_locs[0][0] == "<string>"  # From original source
        lines_in_include = shadow_common_content.count('\n') + 1
        for i in range(1, lines_in_include + 1):
            assert str(shadow_path) in source_locs[i][0]  # From included file
        assert source_locs[-1][0] == "<string>"  # Last line from original source


def test_format_shader_with_line_info():
    """Test formatting shader source with line info for debugging."""
    source_locs = [
        ("file1.glsl", 1, "line1"),
        ("file2.glsl", 5, "  line2"),
        ("file1.glsl", 10, "line3")
    ]
    source = "line1\n  line2\nline3"

    formatted = format_shader_with_line_info(source, source_locs)
    assert "file1.glsl:1" in formatted
    assert "file2.glsl:5" in formatted
    assert "file1.glsl:10" in formatted
    assert "line3" in formatted


def test_conditional_include_and_shared_defines(tmp_path):
    (tmp_path / 'feature.glsl').write_text('#define ENABLED\nfloat feature;')
    source = '#ifdef USE\n#include "feature.glsl"\n#endif\n#ifdef ENABLED\nfloat enabled;\n#endif'
    code, locs = preprocess_shader(source, {'USE': '1'}, [tmp_path])
    assert code == '#define ENABLED\nfloat feature;\nfloat enabled;'
    assert locs[-1][1] == 5
    assert locs[1][:2] == (str(tmp_path / 'feature.glsl'), 2)
    code, _ = preprocess_shader(source, include_dirs=[tmp_path])
    assert code == ''


def test_diamond_and_circular_includes(tmp_path):
    (tmp_path / 'a').write_text('#include "b"\nfloat a;')
    (tmp_path / 'b').write_text('#include "a"\nfloat b;')
    code, locs = preprocess_shader('#include "a"\n#include "b"', include_dirs=[tmp_path])
    assert code.count('float a;') == code.count('float b;') == 1
    assert len(code.splitlines()) == len(locs)


def test_missing_include():
    with pytest.raises(FileNotFoundError, match='missing.glsl'):
        preprocess_shader('#include "missing.glsl"')


def test_empty_format():
    assert format_shader_with_line_info('', []) == ''


def test_shader_manager(capsys):
    from unittest.mock import Mock
    import moderngl
    from wasabi2d.shaders import ShaderManager

    ctx = Mock(extra={})
    manager = ShaderManager(ctx)
    program = manager.load('texquads')
    assert manager.load('texquads') is program
    assert ctx.program.call_count == 1
    assert '#include' not in ctx.program.call_args[1]['fragment_shader']
    ctx.program.side_effect = moderngl.Error('fragment_shader compilation failed')
    with pytest.raises(moderngl.Error):
        manager.load('primitives/particle')
    assert 'textured.frag:1' in capsys.readouterr().out
    manager.release()


def test_all_packaged_shaders():
    from wasabi2d.shader_preprocessor import shaders
    from wasabi2d.shaders import ShaderManager
    from unittest.mock import Mock

    manager = ShaderManager(Mock(extra={}))
    for path in shaders.parent.rglob('*'):
        if path.suffix not in {'.vert', '.frag', '.geom'}:
            continue
        source = manager._read(str(path.relative_to(shaders.parent)))
        assert '#include' not in source
        assert len(source.splitlines()) == len(manager.source_maps[source])
    manager.release()
