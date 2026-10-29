import ast
import re

# Patterns that are dangerous or will crash Manim renderer
BLOCKED_PATTERNS = [
    r"import os",
    r"import sys",
    r"subprocess",
    r"open\(",
    r"exec\(",
    r"eval\(",
    r"__import__",
    r"requests\.",
    r"urllib",
    r"SVGMobject",  # needs external files
    r"ImageMobject",  # needs external files
    r"from manim import \*\s*\n.*import",  # double imports
]

ALLOWED_MANIM_CLASSES = {
    "Text",
    "MathTex",
    "Tex",
    "Write",
    "FadeIn",
    "FadeOut",
    "Transform",
    "ReplacementTransform",
    "Create",
    "Uncreate",
    "Arrow",
    "Rectangle",
    "Circle",
    "Square",
    "Triangle",
    "Line",
    "Dot",
    "NumberPlane",
    "Axes",
    "VGroup",
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "ORIGIN",
    "WHITE",
    "BLACK",
    "BLUE",
    "RED",
    "GREEN",
    "YELLOW",
    "ORANGE",
    "Scene",
    "AnimationGroup",
    "Succession",
    "Wait",
}


def clean_manim_code(code: str) -> str:
    """Strip markdown code fences the LLM wraps around code."""
    # Remove ```python ... ``` or ``` ... ```
    code = re.sub(r"^```(?:python)?\n?", "", code.strip())
    code = re.sub(r"\n?```$", "", code.strip())
    return code.strip()


def validate_manim_code(code: str) -> tuple[bool, str]:
    code = clean_manim_code(code)  # clean first, then validate

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code):
            return False, f"Blocked pattern found: {pattern}"

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in Manim code: {e}"

    has_scene = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Scene":
                    has_scene = True

    if not has_scene:
        return False, "No class inheriting from Scene found"

    return True, ""


def extract_scenes_from_script(llm_output: dict) -> list[dict]:
    scenes = llm_output.get("manim_script", {}).get("scenes", [])
    validated = []

    for i, scene in enumerate(scenes):
        code = clean_manim_code(scene.get("manim_code", ""))
        is_valid, error = validate_manim_code(code)

        if not is_valid:
            print(f"Scene {i + 1} failed validation: {error}")
            continue

        validated.append(
            {
                "scene_index": i + 1,
                "narration": scene.get("narration", ""),
                "duration_seconds": scene.get("duration_seconds", 4),
                "manim_code": code,  # store cleaned code
            }
        )

    return validated
