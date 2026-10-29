"""
Manim Code Generator — TEMPLATE-BASED approach.

THE CORE PRINCIPLE:
1. DO NOT ask the LLM to write Manim positioning code.
2. Visual content comes DIRECTLY from the script JSON's `visual_content` field.
3. If visual_content is missing, fall back to LLM extraction from narration.
4. All templates use HARDCODED safe vertical zones to prevent overlap.
5. Every scene includes a VidhyaGPT watermark in the bottom-right corner.

SAFE VERTICAL ZONES (never violate):
  HEADING_Y   = 2.8    # heading text lives here
  CONTENT_TOP = 1.8    # content starts here
  CONTENT_MID = 0.0    # center content here
  CONTENT_BOT = -2.5   # content ends here (full screen, no avatar)

WATERMARK (bottom-right corner, always visible):
  - Added with self.add() (instant, no animation)
  - color=GRAY, font_size=18
  - to_corner(DR, buff=0.2)

OVERLAP PREVENTION RULES:
  - Every object MUST have explicit position (.move_to / .to_edge / .next_to)
  - Never rely on default ORIGIN — always specify coordinates
  - All VGroups scaled to fit: .scale_to_fit_width(10.5)
  - FadeOut(VGroup(*self.mobjects)) at every scene end
  - Heading always at UP with buff=0.4
"""

import ast
import asyncio
import json
import logging
import re
import subprocess

from video.openai_client import OpenAIClientError, generate_json, generate_with_gpt4

_HAS_OPENAI = True

LOGGER = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# SAFE VERTICAL ZONES — all templates must respect these
# ═══════════════════════════════════════════════════════════════════
HEADING_Y = 2.8
CONTENT_TOP_Y = 1.8
CONTENT_MID_Y = 0.0
CONTENT_BOT_Y = -2.5  # full screen height available (no avatar)

# ═══════════════════════════════════════════════════════════════════
# WATERMARK CODE — injected into every generated scene
# ═══════════════════════════════════════════════════════════════════

def _get_watermark_code() -> str:
    """Returns Manim code that adds VidhyaGPT watermark in bottom-right corner."""
    return """
        # Watermark — bottom right, always visible
        watermark = Text("VidhyaGPT", font_size=18, color=GRAY, weight=NORMAL)
        watermark.to_corner(DR, buff=0.2)
        self.add(watermark)
"""


def _latex_available() -> bool:
    """Check if LaTeX (pdflatex/xelatex) is installed and on PATH."""
    try:
        result = subprocess.run(
            ["latex", "--version"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Cache result so we only check once
_LATEX_OK = None

def _check_latex() -> bool:
    global _LATEX_OK
    if _LATEX_OK is None:
        _LATEX_OK = _latex_available()
        if not _LATEX_OK:
            LOGGER.warning("LaTeX not found on PATH — formulas will use Text instead of MathTex")
    return _LATEX_OK


# ═══════════════════════════════════════════════════════════════════
# CONTENT ZONE CLAMPING — ensures content never goes off screen
# ═══════════════════════════════════════════════════════════════════

def _get_content_clamp_code(group_name: str) -> str:
    """Returns Manim code that clamps a VGroup within visible screen."""
    return f"""
        # Ensure content stays within visible area (y > -3.0)
        if {group_name}.get_bottom()[1] < -3.0:
            {group_name}.shift(UP * (abs({group_name}.get_bottom()[1]) - 3.0 + 0.2))
"""


# ═══════════════════════════════════════════════════════════════════
# CONTENT EXTRACTION (fallback only — used when visual_content missing)
# ═══════════════════════════════════════════════════════════════════

EXTRACT_PROMPT_TEMPLATE = """You are extracting structured visual content from a narration for an educational video scene.
The visual content should show KEY TERMS, FORMULAS, and DEFINITIONS — NOT repeat the narration.

Scene type: {scene_type}
Topic: {topic}
Narration: "{narration}"

Extract VISUAL content as JSON. Keep ALL text SHORT: max 55 characters per line/bullet/step.
DO NOT just repeat the narration. Show key terms and definitions only.

{type_instructions}

Return ONLY valid JSON. No markdown, no backticks.
"""

TYPE_INSTRUCTIONS = {
    "greeting": """Return: {{"heading": "topic name (max 40 chars)", "subtitle": "one welcoming line (max 55 chars)"}}""",
    "bullets": """Return: {{"heading": "heading text (max 40 chars)", "bullets": ["key term 1", "key term 2", "key term 3"]}}
Each bullet max 55 characters. Max 5 bullets. Use KEY TERMS not full sentences.""",
    "formula": """Return: {{"heading": "heading text (max 40 chars)", "formula_tex": "F = ma", "explanation": ["F = Force (N)", "m = Mass (kg)", "a = Acceleration (m/s²)"]}}
IMPORTANT for formula_tex: Use standard LaTeX with DOUBLE backslashes in JSON:
  Fraction: \\\\frac{{a}}{{b}}
  Superscript: T^2
  Subscript: v_0
  Greek: \\\\alpha, \\\\beta, \\\\theta, \\\\omega
  Square root: \\\\sqrt{{x}}
  Proportional: \\\\propto
  Dot product: \\\\cdot
Examples:
  "formula_tex": "F = \\\\frac{{GMm}}{{r^2}}"
  "formula_tex": "KE = \\\\frac{{1}}{{2}}mv^2"
  "formula_tex": "T^2 \\\\propto a^3"
Max 4 explanation lines, each max 55 chars. Format each as: "symbol = meaning (unit)".""",
    "derivation": """Return: {{"heading": "heading text (max 40 chars)", "steps": ["v = u + at", "s = ut + \\\\frac{{1}}{{2}}at^2", "v^2 = u^2 + 2as"]}}
Each step is a valid LaTeX formula string. Use DOUBLE backslashes in JSON for LaTeX commands. Max 4 steps.""",
    "graph": """Return: {{"heading": "heading text (max 40 chars)", "graph_type": "axes_function", "x_label": "Time (s)", "y_label": "Velocity (m/s)", "function": "x", "x_range": [0, 8], "y_range": [0, 8], "description": "short description"}}
function must be a simple Python expression using x (e.g., "x", "x**2", "2*x+1").""",
    "diagram": """Return: {{"heading": "heading text (max 40 chars)", "diagram_type": "orbit|force|wave|atom|ray|geometry|reaction|projectile|circuit|generic", "labels": ["label1", "label2"]}}
diagram_type must be exactly one of: orbit, force, wave, atom, ray, geometry, reaction, projectile, circuit, generic. Max 4 labels.""",
    "example": """Return: {{"heading": "Example", "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."]}}
Max 4 steps, each max 55 characters.""",
    "summary": """Return: {{"heading": "Key Takeaways", "points": ["point 1", "point 2", "point 3"]}}
Max 4 points, each max 55 characters.""",
}


async def extract_scene_content(scene_type: str, narration: str,
                                  visual_content: dict = None, topic: str = "") -> dict | None:
    """Extract structured content. Uses visual_content from script directly if available,
    falls back to GPT-4o, then Gemini for extraction."""

    # If visual_content already has the data we need, use it directly
    if visual_content and isinstance(visual_content, dict):
        if scene_type == "formula" and "formula_tex" in visual_content:
            return visual_content
        if scene_type == "diagram" and "diagram_type" in visual_content:
            return visual_content
        if scene_type == "bullets" and "bullets" in visual_content:
            return visual_content
        if scene_type == "reaction" and "reactants" in visual_content:
            return visual_content
        if scene_type == "summary" and "points" in visual_content:
            return visual_content
        if scene_type == "example" and "steps" in visual_content:
            return visual_content
        if scene_type in ("intro", "greeting") and "heading" in visual_content:
            return visual_content

    instructions = TYPE_INSTRUCTIONS.get(scene_type, TYPE_INSTRUCTIONS["bullets"])
    prompt = EXTRACT_PROMPT_TEMPLATE.format(
        scene_type=scene_type,
        topic=topic,
        narration=narration,
        type_instructions=instructions,
    )

    # Use GPT-4o for extraction
    if _HAS_OPENAI:
        try:
            raw = await generate_with_gpt4(
                system_prompt="You extract structured visual content from narration for educational videos. Return ONLY valid JSON.",
                user_prompt=prompt,
                json_mode=True
            )
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                LOGGER.info("Content extracted via GPT-4o for %s", scene_type)
                return parsed
        except Exception as exc:
            LOGGER.warning("GPT-4o extraction failed for %s: %s", scene_type, exc)

    # Fallback: sync GPT-4o via generate_json
    try:
        raw = await asyncio.to_thread(generate_json, prompt, 0.1, 1000)
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return None
        return parsed
    except (OpenAIClientError, json.JSONDecodeError, ValueError) as exc:
        LOGGER.warning("Content extraction failed for %s: %s", scene_type, exc)
        return None


def _split_narration_to_bullets(narration: str, max_len: int = 55) -> list[str]:
    """Split narration into chunks suitable for bullet display."""
    words = narration.split()
    lines = []
    current = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) >= max_len:
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))
    return lines[:5]  # max 5 bullets


def _safe(text: str, max_len: int = 55) -> str:
    """Sanitize text for Manim: remove quotes, limit length."""
    safe = text.replace('"', "'").replace("\\", "\\\\")
    if len(safe) > max_len:
        safe = safe[:max_len - 3] + "..."
    return safe


def sanitize_formula_tex(formula_tex: str) -> str:
    """
    Fix backslash issues from JSON parsing of LaTeX formulas.

    Handles 3 scenarios:
    A. JSON \\f → form feed char + "rac" → restore to \\frac
    B. Bare "frac{" without backslash → add \\frac{
    C. Double-escaped \\\\frac → collapse to \\frac
    """
    if not formula_tex or not formula_tex.strip():
        return None

    tex = formula_tex.replace('"', '').replace("'", "")

    # Step 1: Fix control characters produced by JSON parsing
    # JSON \\f = formfeed, \\t = tab, \\n = newline, \\r = CR, \\b = backspace
    tex = tex.replace('\f', '\\f')
    tex = tex.replace('\t', '\\t')
    tex = tex.replace('\n', '\\n')
    tex = tex.replace('\r', '\\r')
    tex = tex.replace('\b', '\\b')

    # Step 2: Collapse double+ backslashes to single
    while '\\\\' in tex:
        tex = tex.replace('\\\\', '\\')

    # Step 3: Detect bare LaTeX commands (no preceding backslash) and add one
    latex_commands = [
        'frac', 'sqrt', 'sum', 'int', 'prod', 'lim',
        'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta',
        'lambda', 'mu', 'pi', 'rho', 'sigma', 'omega', 'Omega',
        'phi', 'psi', 'eta', 'tau', 'nu', 'xi',
        'infty', 'partial', 'nabla', 'cdot', 'times', 'div',
        'leq', 'geq', 'neq', 'approx', 'propto', 'equiv',
        'left', 'right', 'text', 'mathrm', 'mathbf',
        'vec', 'hat', 'bar', 'dot', 'ddot',
        'rightarrow', 'leftarrow', 'Rightarrow', 'Downarrow',
        'pm', 'mp', 'circ', 'degree',
    ]
    for cmd in latex_commands:
        # Add backslash if not already preceded by one
        # Use raw strings for both pattern and replacement to avoid regex escape issues
        pattern = r'(?<!\\)\b' + cmd + r'(?=[^a-zA-Z]|$)'
        replacement = r'\\' + cmd
        tex = re.sub(pattern, replacement, tex)

    return tex.strip()


# ── Unicode mapping tables for no-LaTeX fallback ──
_UNICODE_SUP = {
    '0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵',
    '6':'⁶','7':'⁷','8':'⁸','9':'⁹','n':'ⁿ','+':'⁺','-':'⁻',
}
_UNICODE_SUB = {
    '0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅',
    '6':'₆','7':'₇','8':'₈','9':'₉',
}
_UNICODE_GREEK = {
    '\\alpha':'α','\\beta':'β','\\gamma':'γ','\\delta':'δ','\\epsilon':'ε',
    '\\theta':'θ','\\lambda':'λ','\\mu':'μ','\\pi':'π','\\rho':'ρ',
    '\\sigma':'σ','\\omega':'ω','\\Omega':'Ω','\\phi':'φ','\\psi':'ψ',
    '\\eta':'η','\\tau':'τ','\\nu':'ν','\\xi':'ξ',
}
_UNICODE_OPS = {
    '\\times':'×','\\cdot':'·','\\pm':'±','\\mp':'∓',
    '\\leq':'≤','\\geq':'≥','\\neq':'≠','\\approx':'≈',
    '\\propto':'∝','\\infty':'∞','\\equiv':'≡',
    '\\rightarrow':'→','\\leftarrow':'←','\\Rightarrow':'⇒',
}


def _apply_unicode(text: str) -> str:
    """Convert LaTeX notation to readable Unicode: ^2→², \\alpha→α, etc."""
    # Superscripts: ^{2} → ² and ^2 → ²
    for k, v in _UNICODE_SUP.items():
        text = text.replace(f'^{{{k}}}', v)
        text = text.replace(f'^{k}', v)
    # Subscripts: _{0} → ₀ and _0 → ₀
    for k, v in _UNICODE_SUB.items():
        text = text.replace(f'_{{{k}}}', v)
        text = text.replace(f'_{k}', v)
    # Greek letters
    for k, v in _UNICODE_GREEK.items():
        text = text.replace(k, v)
    # Operators
    for k, v in _UNICODE_OPS.items():
        text = text.replace(k, v)
    # \\sqrt{x} → √(x)
    text = re.sub(r'\\sqrt\{([^}]*)\}', r'√(\1)', text)
    text = text.replace('\\sqrt', '√')
    # Remove any remaining \\command → command
    text = re.sub(r'\\([a-zA-Z]+)', r'\1', text)
    # Clean braces
    text = text.replace('{', '').replace('}', '')
    return text


def _latex_to_display(tex: str) -> str:
    """Convert LaTeX formula to readable Unicode text (for derivation steps etc)."""
    display = tex
    # \\frac{a}{b} → (a)/(b)
    display = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'(\1)/(\2)', display)
    display = _apply_unicode(display)
    return display


def _parse_frac(formula: str):
    """
    Parse \\\\frac{num}{den} from a LaTeX formula.
    Returns (prefix, numerator, denominator, suffix) or None.
    """
    idx = formula.find('\\frac')
    if idx == -1:
        return None
    prefix = formula[:idx].strip()
    rest = formula[idx + 5:]  # skip \\frac

    # Extract {numerator}
    if not rest or rest[0] != '{':
        return None
    depth, end = 0, -1
    for i, c in enumerate(rest):
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None
    numerator = rest[1:end]
    rest = rest[end + 1:]

    # Extract {denominator}
    if not rest or rest[0] != '{':
        return None
    depth, end = 0, -1
    for i, c in enumerate(rest):
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None
    denominator = rest[1:end]
    suffix = rest[end + 1:].strip()

    return (prefix, numerator, denominator, suffix)


def _build_visual_formula_code(formula_clean: str) -> str:
    """
    Generate Manim code to render a formula visually using Text + Line.
    Produces proper textbook-style fractions WITHOUT needing LaTeX.

    For F = \\\\frac{GMm}{r^2}, generates:
        GMm
    F = ────
        r²
    """
    parts = _parse_frac(formula_clean)

    if parts:
        prefix, numerator, denominator, suffix = parts
        # Convert to Unicode display
        prefix_d = _apply_unicode(prefix).strip().replace('"', "'")
        num_d = _apply_unicode(numerator).strip().replace('"', "'")
        den_d = _apply_unicode(denominator).strip().replace('"', "'")
        suffix_d = _apply_unicode(suffix).strip().replace('"', "'")

        # Add spacing after prefix
        if prefix_d and not prefix_d.endswith(' '):
            prefix_d += '  '

        lines = []
        lines.append('        # Build visual fraction (no LaTeX needed)')

        if prefix_d:
            lines.append(f'        _pf = Text("{prefix_d}", font_size=48, color=BLUE, weight=BOLD)')

        lines.append(f'        _num = Text("{num_d}", font_size=38, color=BLUE, weight=BOLD)')
        lines.append(f'        _den = Text("{den_d}", font_size=38, color=BLUE, weight=BOLD)')
        lines.append(f'        _bar = Line(LEFT, RIGHT, color=BLUE, stroke_width=2)')
        lines.append(f'        _bar.set_width(max(_num.width, _den.width) + 0.3)')
        lines.append(f'        _num.next_to(_bar, UP, buff=0.08)')
        lines.append(f'        _den.next_to(_bar, DOWN, buff=0.08)')
        lines.append(f'        _frac = VGroup(_num, _bar, _den)')

        arrange_parts = []
        if prefix_d:
            arrange_parts.append('_pf')
        arrange_parts.append('_frac')

        if suffix_d:
            lines.append(f'        _sf = Text("{suffix_d}", font_size=48, color=BLUE, weight=BOLD)')
            arrange_parts.append('_sf')

        parts_str = ', '.join(arrange_parts)
        lines.append(f'        formula = VGroup({parts_str}).arrange(RIGHT, buff=0.15)')

        return '\n'.join(lines)
    else:
        # No fraction — use Unicode text
        display = _apply_unicode(formula_clean).replace('"', "'")
        return f'        formula = Text("{display}", font_size=48, color=BLUE, weight=BOLD)'


# ═══════════════════════════════════════════════════════════════════
# HARDCODED MANIM TEMPLATE FUNCTIONS
# All templates follow these rules:
#   1. Watermark added with self.add() at start of every scene
#   2. Heading at UP with buff=0.4 (y ≈ 2.8)
#   3. Content in safe zone (y = 1.8 down to -2.5)
#   4. VGroups use .arrange() with explicit buff
#   5. All groups scaled: .scale_to_fit_width(10.5)
#   6. Content uses full screen (no avatar zone restriction)
#   7. FadeOut(VGroup(*self.mobjects)) at scene end
# ═══════════════════════════════════════════════════════════════════

def make_greeting_scene(class_name: str, title: str, subtitle: str, duration: float) -> str:
    safe_title = _safe(title, 40)
    safe_sub = _safe(subtitle, 55)
    wait = max(0.5, duration - 4.5)
    watermark_code = _get_watermark_code()
    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Branding — top of screen
        brand = Text("VidhyaGPT", font_size=28, color=BLUE)
        brand.to_edge(UP, buff=0.4)
        self.play(FadeIn(brand), run_time=0.8)

        # Topic title — centered in content zone
        title = Text("{safe_title}", font_size=42, color=YELLOW)
        title.move_to(UP * 0.5)
        if title.width > 10.5:
            title.scale_to_fit_width(10.5)
        self.play(Write(title), run_time=1.5)

        # Subtitle — explicitly below title
        subtitle = Text("{safe_sub}", font_size=26, color=WHITE)
        subtitle.next_to(title, DOWN, buff=0.6)
        if subtitle.width > 10.5:
            subtitle.scale_to_fit_width(10.5)
        self.play(FadeIn(subtitle), run_time=1.0)

        self.wait({wait:.1f})

        # Clear everything
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def make_bullets_scene(class_name: str, heading: str, bullets: list[str], duration: float) -> str:
    safe_heading = _safe(heading, 40)
    bullet_lines = [_safe(b, 55) for b in bullets[:5]]
    n = len(bullet_lines)
    anim_time = n * 0.6 + 2.5
    wait = max(0.5, duration - anim_time - 0.7)
    watermark_code = _get_watermark_code()
    clamp_code = _get_content_clamp_code("bullets")

    bullets_code = ""
    for i, b in enumerate(bullet_lines):
        bullets_code += f'''
        b{i} = Text("• {b}", font_size=26, color=WHITE)'''

    arrange_items = ", ".join(f"b{i}" for i in range(n))

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Heading — always at top
        heading = Text("{safe_heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)
{bullets_code}

        # Arrange bullets with explicit spacing
        bullets = VGroup({arrange_items})
        bullets.arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        bullets.scale_to_fit_width(min(bullets.width, 10.5))
        bullets.move_to(ORIGIN + DOWN * 0.2)
{clamp_code}
        # Animate each bullet
        for b in bullets:
            self.play(FadeIn(b, shift=RIGHT * 0.3), run_time=0.6)

        self.wait({wait:.1f})

        # Clear everything
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def make_formula_scene(class_name: str, heading: str, formula_tex: str, explanation_lines: list[str], duration: float) -> str:
    """
    Renders a formula using MathTex (if LaTeX available) or Text (fallback).
    Uses repr() to safely embed the formula string in generated code.
    """
    safe_heading = _safe(heading, 40)
    formula_clean = sanitize_formula_tex(formula_tex)
    if formula_clean is None:
        # If formula is empty/invalid, use the raw text or a safe fallback
        formula_clean = formula_tex.strip() if formula_tex and formula_tex.strip() else heading
    use_latex = _check_latex()

    exp_lines = [_safe(e, 55) for e in explanation_lines[:4]]
    n = len(exp_lines)
    anim_time = 0.8 + 0.2 + 2.0 + 0.8 + n * 0.5 + 1.0 + 0.5
    wait = max(0.5, duration - anim_time - 0.7)
    watermark_code = _get_watermark_code()
    clamp_code = _get_content_clamp_code("explanations")

    # Formula rendering
    if use_latex:
        formula_repr = repr(formula_clean)
        formula_code = f'        formula = MathTex({formula_repr}, font_size=72, color=BLUE)'
    else:
        # Build visual formula with proper textbook-style fractions
        formula_code = _build_visual_formula_code(formula_clean)

    # Build explanation Text objects
    exp_code = ""
    for i, e in enumerate(exp_lines):
        safe_e = e.replace('\\', '')
        exp_code += f'''
        e{i} = Text("{safe_e}", font_size=26, color=WHITE)'''

    arrange_items = ", ".join(f"e{i}" for i in range(n))

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Heading
        heading = Text("{safe_heading}", font_size=34, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)

{formula_code}
        formula.move_to(UP * 0.8)
        if formula.width > 10.5:
            formula.scale_to_fit_width(10.5)
        self.play(Write(formula), run_time=2.0)

        # Highlight box
        formula_box = SurroundingRectangle(formula, color=YELLOW, buff=0.25, corner_radius=0.1)
        self.play(Create(formula_box), run_time=0.8)
        self.wait(0.4)
{exp_code}

        # Explanations below formula — with guaranteed spacing
        explanations = VGroup({arrange_items})
        explanations.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        explanations.scale_to_fit_width(min(explanations.width, 10.0))
        explanations.next_to(formula_box, DOWN, buff=0.8)
        # Hard clamp: ensure explanations never go off screen
        if explanations.get_bottom()[1] < -3.0:
            explanations.shift(UP * (abs(explanations.get_bottom()[1]) - 3.0 + 0.15))
        # Hard clamp: ensure explanations never overlap formula box
        if explanations.get_top()[1] > formula_box.get_bottom()[1] - 0.3:
            explanations.shift(DOWN * (explanations.get_top()[1] - formula_box.get_bottom()[1] + 0.4))
{clamp_code}
        for e in explanations:
            self.play(FadeIn(e, shift=UP * 0.15), run_time=0.5)
            self.wait(0.25)

        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def make_derivation_scene(class_name: str, heading: str, steps: list[str], duration: float) -> str:
    """
    Shows step-by-step mathematical derivation.
    Uses repr() to safely embed LaTeX formulas in generated code.
    """
    safe_heading = _safe(heading, 40)
    step_formulas = [sanitize_formula_tex(s) for s in steps[:4]]
    n = len(step_formulas)
    anim_time = 0.8 + 0.2 + n * 1.8 + 1.0 + 0.5
    wait = max(0.5, duration - anim_time - 0.7)
    watermark_code = _get_watermark_code()
    use_latex = _check_latex()

    # Build the step objects using repr() for safe backslash handling
    steps_code = ""
    for i, s in enumerate(step_formulas):
        if use_latex:
            s_repr = repr(s)
            steps_code += f'''
        step{i} = MathTex({s_repr}, font_size=48, color=WHITE)'''
        else:
            display_s = _latex_to_display(s)
            display_s = display_s.replace('"', "'").replace('\\', '')
            steps_code += f'''
        step{i} = Text("{display_s}", font_size=36, color=WHITE)'''

    # Build the arrows and arrangement code
    if use_latex:
        downarrow_repr = repr('\\Downarrow')
    else:
        downarrow_repr = repr('\u2193')

    arrange_code = f"""
        # Arrange all steps vertically with arrows between them
        step0.move_to(UP * 1.2)
        if step0.width > 10.5:
            step0.scale_to_fit_width(10.5)
        self.play(Write(step0), run_time=1.5)
"""

    for i in range(1, n):
        if use_latex:
            arrow_line = f'        arrow{i} = MathTex({downarrow_repr}, font_size=36, color=YELLOW)'
        else:
            arrow_line = f'        arrow{i} = Text({downarrow_repr}, font_size=36, color=YELLOW)'
        arrange_code += f"""
{arrow_line}
        arrow{i}.next_to(step{i - 1}, DOWN, buff=0.25)
        self.play(FadeIn(arrow{i}), run_time=0.3)

        step{i}.next_to(arrow{i}, DOWN, buff=0.25)
        if step{i}.width > 10.5:
            step{i}.scale_to_fit_width(10.5)
        if step{i}.get_bottom()[1] < -3.0:
            step{i}.shift(UP * (abs(step{i}.get_bottom()[1]) - 3.0 + 0.2))
        self.play(Write(step{i}), run_time=1.5)
"""

    # Highlight the final result
    highlight_code = f"""
        # Highlight final result
        final_box = SurroundingRectangle(step{n - 1}, color=GREEN, buff=0.2, corner_radius=0.1)
        self.play(Create(final_box), run_time=0.7)
""" if n > 0 else ""

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Heading
        heading = Text("{safe_heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)
{steps_code}
{arrange_code}{highlight_code}
        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def make_graph_scene(class_name: str, heading: str, graph_data: dict, duration: float) -> str:
    """
    Renders a graph/chart using Manim's built-in Axes.
    Supports: axes_function (plots a Python function expression).
    """
    safe_heading = _safe(heading, 40)

    graph_type = graph_data.get("graph_type", "axes_function")
    x_label = _safe(graph_data.get("x_label", "X"), 25)
    y_label = _safe(graph_data.get("y_label", "Y"), 25)
    func_expr = graph_data.get("function", "x")
    x_range = graph_data.get("x_range", [0, 10])
    y_range = graph_data.get("y_range", [0, 10])
    description = _safe(graph_data.get("description", ""), 55)

    # Sanitize function expression — only allow safe math operations
    safe_func = _sanitize_function_expr(func_expr)

    # Calculate x/y step sizes
    x_span = max(1, x_range[1] - x_range[0])
    y_span = max(1, y_range[1] - y_range[0])
    x_step = max(1, x_span // 5)
    y_step = max(1, y_span // 5)

    anim_time = 0.8 + 0.2 + 1.5 + 0.5 + 2.0 + 1.0 + 0.5
    wait = max(0.5, duration - anim_time - 0.7)
    watermark_code = _get_watermark_code()

    desc_code = ""
    if description:
        desc_code = f'''
        # Description label
        desc = Text("{description}", font_size=20, color=GRAY)
        desc.next_to(axes, DOWN, buff=0.3)
        if desc.width > 10.5:
            desc.scale_to_fit_width(10.5)
        if desc.get_bottom()[1] < -3.0:
            desc.move_to(DOWN * 2.5)
        self.play(FadeIn(desc), run_time=0.5)
'''

    return f'''from manim import *
import math

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Heading — always at top
        heading = Text("{safe_heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)

        # Create axes — full height available
        axes = Axes(
            x_range=[{x_range[0]}, {x_range[1]}, {x_step}],
            y_range=[{y_range[0]}, {y_range[1]}, {y_step}],
            x_length=8,
            y_length=4.0,
            axis_config={{"color": WHITE, "include_tip": True, "font_size": 20}},
            x_axis_config={{"numbers_to_include": list(range({x_range[0]}, {x_range[1]} + 1, {x_step}))    }},
            y_axis_config={{"numbers_to_include": list(range({y_range[0]}, {y_range[1]} + 1, {y_step}))}},
        )
        axes.move_to(DOWN * 0.3)

        # Axis labels
        x_lab = Text("{x_label}", font_size=20, color=WHITE)
        x_lab.next_to(axes.x_axis, DOWN, buff=0.25)
        y_lab = Text("{y_label}", font_size=20, color=WHITE)
        y_lab.next_to(axes.y_axis, LEFT, buff=0.25)
        y_lab.rotate(90 * DEGREES)

        self.play(Create(axes), FadeIn(x_lab), FadeIn(y_lab), run_time=1.5)

        # Plot the function
        graph = axes.plot(
            lambda x: {safe_func},
            color=BLUE,
            stroke_width=3,
            x_range=[{x_range[0]}, {x_range[1]}],
        )
        self.play(Create(graph), run_time=2.0)
{desc_code}
        self.wait({wait:.1f})

        # Clear everything
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def _sanitize_function_expr(expr: str) -> str:
    """
    Sanitize a function expression to be safe for eval inside a lambda.
    Only allows basic math operations.
    """
    allowed_chars = set("0123456789xX+-*/.() ")
    allowed_funcs = {"sin", "cos", "tan", "sqrt", "abs", "log", "exp", "pi", "math"}

    sanitized = expr.strip()

    # Replace common math notations
    sanitized = sanitized.replace("^", "**")
    sanitized = sanitized.replace("×", "*")
    sanitized = sanitized.replace("÷", "/")

    # Check for any dangerous patterns
    for char in sanitized:
        if char not in allowed_chars and not char.isalpha():
            sanitized = "x"  # fallback to y=x
            break

    # If it contains function calls, validate them
    import re as _re
    func_calls = _re.findall(r'([a-zA-Z]+)\s*\(', sanitized)
    for fc in func_calls:
        if fc.lower() not in allowed_funcs:
            sanitized = "x"  # fallback to y=x
            break

    # Prefix math functions with math.
    for fn in ["sin", "cos", "tan", "sqrt", "log", "exp"]:
        sanitized = _re.sub(rf'\b{fn}\b', f'math.{fn}', sanitized)

    if not sanitized:
        sanitized = "x"

    return sanitized


def make_diagram_scene(class_name: str, heading: str, diagram_type: str, labels: list[str], duration: float) -> str:
    safe_heading = _safe(heading, 40)

    if diagram_type == "orbit":
        return _make_orbit_diagram(class_name, safe_heading, labels, duration)
    elif diagram_type == "force":
        return _make_force_diagram(class_name, safe_heading, labels, duration)
    elif diagram_type == "wave":
        return _make_wave_diagram(class_name, safe_heading, labels, duration)
    elif diagram_type == "atom":
        return _make_atom_diagram(class_name, safe_heading, labels, duration)
    elif diagram_type == "ray":
        return _make_ray_diagram(class_name, safe_heading, labels, duration)
    elif diagram_type == "geometry":
        return _make_geometry_diagram(class_name, safe_heading, labels, duration)
    elif diagram_type == "reaction":
        return _make_reaction_diagram(class_name, safe_heading, labels, duration)
    elif diagram_type == "projectile":
        return _make_projectile_diagram(class_name, safe_heading, labels, duration)
    elif diagram_type == "circuit":
        return _make_circuit_diagram(class_name, safe_heading, labels, duration)
    else:
        # generic falls back to bullets
        return make_bullets_scene(class_name, heading, labels, duration)


def _make_orbit_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    sun_label = _safe(labels[0] if len(labels) > 0 else "Sun", 20)
    planet_label = _safe(labels[1] if len(labels) > 1 else "Planet", 20)
    wait = max(0.5, duration - 7.5)
    watermark_code = _get_watermark_code()

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Heading — always at top
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)

        # Sun at center of content zone
        sun = Circle(radius=0.4, color=YELLOW, fill_opacity=0.8)
        sun.move_to(DOWN * 0.1)
        sun_label = Text("{sun_label}", font_size=20, color=YELLOW)
        sun_label.next_to(sun, DOWN, buff=0.2)
        self.play(GrowFromCenter(sun), FadeIn(sun_label), run_time=1.0)

        # Orbit path
        orbit = Circle(radius=2.0, color=BLUE_B, stroke_opacity=0.5)
        orbit.move_to(sun.get_center())
        self.play(Create(orbit), run_time=1.0)

        # Planet
        planet = Circle(radius=0.15, color=GREEN, fill_opacity=1, stroke_width=0)
        planet.move_to(orbit.point_from_proportion(0))
        planet_label = Text("{planet_label}", font_size=20, color=GREEN)
        planet_label.next_to(planet, UP, buff=0.2)
        self.play(GrowFromCenter(planet), FadeIn(planet_label), run_time=0.5)

        # Animate planet along orbit
        self.play(
            MoveAlongPath(planet, orbit, rate_func=linear),
            run_time=3.0,
        )

        self.wait({wait:.1f})

        # Clear everything
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def _make_force_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    obj_label = _safe(labels[0] if len(labels) > 0 else "Object", 20)
    force_label = _safe(labels[1] if len(labels) > 1 else "Force", 20)
    wait = max(0.5, duration - 5.5)
    watermark_code = _get_watermark_code()

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Heading — always at top
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)

        # Object — in content zone, left side
        obj = Square(side_length=1.2, color=BLUE, fill_opacity=0.5)
        obj.move_to(LEFT * 1.5 + DOWN * 0.1)
        obj_text = Text("{obj_label}", font_size=20, color=WHITE)
        obj_text.move_to(obj.get_center())
        self.play(DrawBorderThenFill(obj), FadeIn(obj_text), run_time=1.0)

        # Force arrow — explicitly to the right of object
        arrow = Arrow(
            start=obj.get_right() + RIGHT * 0.1,
            end=obj.get_right() + RIGHT * 2.5,
            color=RED, buff=0,
        )
        force_text = Text("{force_label}", font_size=22, color=RED)
        force_text.next_to(arrow, UP, buff=0.2)
        self.play(Create(arrow), FadeIn(force_text), run_time=1.0)

        self.wait({wait:.1f})

        # Clear everything
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def _make_wave_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    wave_label = _safe(labels[0] if len(labels) > 0 else "Wave", 20)
    wait = max(0.5, duration - 6.0)
    watermark_code = _get_watermark_code()

    return f'''from manim import *
import numpy as np

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)

        axes = Axes(
            x_range=[0, 4 * PI, PI / 2],
            y_range=[-2, 2, 1],
            x_length=10,
            y_length=3.5,
            axis_config={{"color": WHITE}},
        )
        axes.move_to(DOWN * 0.3)
        self.play(Create(axes), run_time=1.0)

        wave = axes.plot(lambda x: np.sin(x), color=BLUE, stroke_width=3)
        wave_label = Text("{wave_label}", font_size=22, color=BLUE)
        wave_label.next_to(axes, DOWN, buff=0.3)
        self.play(Create(wave), FadeIn(wave_label), run_time=2.0)

        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def _make_atom_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    nucleus_label = _safe(labels[0] if len(labels) > 0 else "Nucleus", 20)
    wait = max(0.5, duration - 6.0)
    watermark_code = _get_watermark_code()

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)

        # Nucleus
        nucleus = Circle(radius=0.5, color=RED, fill_opacity=0.8)
        nucleus.move_to(DOWN * 0.1)
        nuc_text = Text("{nucleus_label}", font_size=18, color=WHITE)
        nuc_text.move_to(nucleus.get_center())
        self.play(GrowFromCenter(nucleus), FadeIn(nuc_text), run_time=1.0)

        # Electron orbits
        orbit1 = Circle(radius=1.2, color=BLUE_B, stroke_opacity=0.4).move_to(nucleus.get_center())
        orbit2 = Circle(radius=1.8, color=BLUE_B, stroke_opacity=0.4).move_to(nucleus.get_center())
        self.play(Create(orbit1), Create(orbit2), run_time=0.8)

        # Electrons
        e1 = Circle(radius=0.1, color=BLUE, fill_opacity=1, stroke_width=0)
        e1.move_to(orbit1.point_from_proportion(0))
        e2 = Circle(radius=0.1, color=BLUE, fill_opacity=1, stroke_width=0)
        e2.move_to(orbit2.point_from_proportion(0.25))
        self.play(GrowFromCenter(e1), GrowFromCenter(e2), run_time=0.5)

        self.play(
            MoveAlongPath(e1, orbit1, rate_func=linear),
            MoveAlongPath(e2, orbit2, rate_func=linear),
            run_time=2.5,
        )

        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def _make_ray_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    wait = max(0.5, duration - 5.5)
    watermark_code = _get_watermark_code()

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)

        # Mirror / lens
        mirror = Line(UP * 1.5 + RIGHT * 1, DOWN * 1.5 + RIGHT * 1, color=BLUE, stroke_width=3)
        mirror.move_to(RIGHT * 1)
        self.play(Create(mirror), run_time=0.5)

        # Incident ray
        incident = Arrow(LEFT * 3 + UP * 0.8, RIGHT * 1 + UP * 0.0, color=YELLOW, buff=0)
        inc_label = Text("Incident", font_size=18, color=YELLOW).next_to(incident, UP, buff=0.1)
        self.play(Create(incident), FadeIn(inc_label), run_time=1.0)

        # Reflected ray
        reflected = Arrow(RIGHT * 1, RIGHT * 4 + UP * 0.8, color=GREEN, buff=0)
        ref_label = Text("Reflected", font_size=18, color=GREEN).next_to(reflected, UP, buff=0.1)
        self.play(Create(reflected), FadeIn(ref_label), run_time=1.0)

        # Normal line
        normal = DashedLine(UP * 1.5 + RIGHT * 1, DOWN * 1.5 + RIGHT * 1, color=GRAY)
        normal.rotate(90 * DEGREES)
        normal.move_to(RIGHT * 1)
        norm_label = Text("Normal", font_size=16, color=GRAY).next_to(normal, DOWN, buff=0.1)
        self.play(Create(normal), FadeIn(norm_label), run_time=0.5)

        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def _make_geometry_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    wait = max(0.5, duration - 5.5)
    watermark_code = _get_watermark_code()
    label_a = _safe(labels[0] if len(labels) > 0 else "A", 10)
    label_b = _safe(labels[1] if len(labels) > 1 else "B", 10)
    label_c = _safe(labels[2] if len(labels) > 2 else "C", 10)

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)

        # Triangle
        A = [-2, -1.5, 0]
        B = [2, -1.5, 0]
        C = [0, 1.5, 0]
        triangle = Polygon(A, B, C, color=BLUE, fill_opacity=0.2, stroke_width=3)
        self.play(Create(triangle), run_time=1.0)

        # Labels
        la = Text("{label_a}", font_size=22, color=WHITE).next_to(triangle, LEFT + DOWN, buff=0.1)
        lb = Text("{label_b}", font_size=22, color=WHITE).next_to(triangle, RIGHT + DOWN, buff=0.1)
        lc = Text("{label_c}", font_size=22, color=WHITE).next_to(triangle, UP, buff=0.1)
        self.play(FadeIn(la), FadeIn(lb), FadeIn(lc), run_time=0.5)

        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def _make_reaction_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    """Legacy reaction diagram — simple reactant → product with boxes."""
    reactant = _safe(labels[0] if len(labels) > 0 else "Reactant", 30)
    product = _safe(labels[1] if len(labels) > 1 else "Product", 30)
    condition = _safe(labels[2] if len(labels) > 2 else "", 30)
    wait = max(0.5, duration - 6.0)
    watermark_code = _get_watermark_code()

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)

        # Reactant box
        r_text = Text("{reactant}", font_size=28, color=ORANGE)
        r_box = SurroundingRectangle(r_text, color=ORANGE, buff=0.3, corner_radius=0.1)
        reactant_group = VGroup(r_box, r_text).move_to(LEFT * 3)
        self.play(FadeIn(reactant_group), run_time=0.8)

        # Arrow
        arrow = Arrow(LEFT * 1.2, RIGHT * 1.2, color=WHITE, buff=0.1)
        arrow.move_to(ORIGIN)
        self.play(Create(arrow), run_time=0.5)

        # Condition label (above arrow)
        if "{condition}":
            cond = Text("{condition}", font_size=18, color=GRAY)
            cond.next_to(arrow, UP, buff=0.15)
            self.play(FadeIn(cond), run_time=0.3)

        # Product box
        p_text = Text("{product}", font_size=28, color=PURPLE)
        p_box = SurroundingRectangle(p_text, color=PURPLE, buff=0.3, corner_radius=0.1)
        product_group = VGroup(p_box, p_text).move_to(RIGHT * 3)
        self.play(FadeIn(product_group), run_time=0.8)

        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def make_reaction_diagram(class_name: str, heading: str, reactants: list, products: list,
                           conditions: str, duration: float, catalyst: str = "",
                           temp_condition: str = "", full_equation: str = "",
                           intermediate: dict = None) -> str:
    """
    Renders chemical reaction with hexagonal benzene structures.
    Supports 2-step reactions with 3 hexagons (like Sandmeyer).
    intermediate: optional dict for middle compound in 2-step reaction.
    """
    heading_safe = heading.replace('"', "'")[:50]
    cond_safe = conditions.replace('"', "'").replace('\\', '')[:40] if conditions else ""
    temp_safe = temp_condition.replace('"', "'")[:30] if temp_condition else ""
    catalyst_safe = catalyst.replace('"', "'")[:30] if catalyst else ""

    has_intermediate = intermediate is not None

    if has_intermediate:
        # 3-hexagon layout: reactant → intermediate → product
        r = reactants[0] if reactants else {"symbol": "Ar", "group": "NH_2", "color": "ORANGE"}
        inter = intermediate
        p = products[0] if products else {"symbol": "Ar", "group": "Z", "color": "BLUE"}

        r_sym = str(r.get("symbol", "Ar")).replace('"', "'")[:10]
        r_grp = str(r.get("group", "")).replace('"', "'")[:15]
        r_col = str(r.get("color", "ORANGE"))

        i_sym = str(inter.get("symbol", "Ar")).replace('"', "'")[:10]
        i_grp = str(inter.get("group", "")).replace('"', "'")[:15]
        i_col = str(inter.get("color", "PURPLE"))

        p_sym = str(p.get("symbol", "Ar")).replace('"', "'")[:10]
        p_grp = str(p.get("group", "")).replace('"', "'")[:15]
        p_col = str(p.get("color", "BLUE"))

        hex_code = f"""
        # Reactant hexagon
        hex_r = RegularPolygon(n=6, color={r_col}, stroke_width=3)
        hex_r.scale(0.75)
        hex_r.move_to([-4.0, -0.2, 0])
        lbl_r = Text("{r_sym}", font_size=28, color=WHITE)
        lbl_r.move_to([-4.0, -0.2, 0])
        grp_r = MathTex(r"{r_grp}", font_size=28, color=GREEN)
        grp_r.next_to(hex_r, UP, buff=0.18)

        # Intermediate hexagon
        hex_i = RegularPolygon(n=6, color={i_col}, stroke_width=3)
        hex_i.scale(0.75)
        hex_i.move_to([0.0, -0.2, 0])
        lbl_i = Text("{i_sym}", font_size=28, color=WHITE)
        lbl_i.move_to([0.0, -0.2, 0])
        grp_i = MathTex(r"{i_grp}", font_size=28, color=GREEN)
        grp_i.next_to(hex_i, UP, buff=0.18)

        # Product hexagon
        hex_p = RegularPolygon(n=6, color={p_col}, stroke_width=3)
        hex_p.scale(0.75)
        hex_p.move_to([4.0, -0.2, 0])
        lbl_p = Text("{p_sym}", font_size=28, color=WHITE)
        lbl_p.move_to([4.0, -0.2, 0])
        grp_p = MathTex(r"{p_grp}", font_size=28, color=GREEN)
        grp_p.next_to(hex_p, UP, buff=0.18)

        # Arrow 1: reactant → intermediate
        arrow1 = Arrow([-2.7, -0.2, 0], [-1.3, -0.2, 0], color=WHITE, stroke_width=4, buff=0)
        cond1 = Text("{cond_safe}", font_size=18, color=WHITE)
        cond1.next_to(arrow1, DOWN, buff=0.15)
        temp1 = Text("{temp_safe}", font_size=18, color=BLUE)
        temp1.next_to(cond1, DOWN, buff=0.1)

        # Arrow 2: intermediate → product
        arrow2 = Arrow([1.3, -0.2, 0], [2.7, -0.2, 0], color=WHITE, stroke_width=4, buff=0)
        cat2 = Text("{catalyst_safe}", font_size=18, color=ORANGE)
        cat2.next_to(arrow2, DOWN, buff=0.15)

        self.play(Create(hex_r), Write(lbl_r), Write(grp_r))
        self.wait(0.3)
        self.play(Create(arrow1), Write(cond1), Write(temp1))
        self.wait(0.3)
        self.play(Create(hex_i), Write(lbl_i), Write(grp_i))
        self.wait(0.3)
        self.play(Create(arrow2), Write(cat2))
        self.wait(0.3)
        self.play(Create(hex_p), Write(lbl_p), Write(grp_p))
"""
    else:
        # 2-hexagon layout: reactant → product
        r = reactants[0] if reactants else {"symbol": "Ar", "group": "NH_2", "color": "ORANGE"}
        p = products[0] if products else {"symbol": "Ar", "group": "N_2^+", "color": "PURPLE"}

        r_sym = str(r.get("symbol", "Ar")).replace('"', "'")[:10]
        r_grp = str(r.get("group", "")).replace('"', "'")[:15]
        r_col = str(r.get("color", "ORANGE"))

        p_sym = str(p.get("symbol", "Ar")).replace('"', "'")[:10]
        p_grp = str(p.get("group", "")).replace('"', "'")[:15]
        p_col = str(p.get("color", "PURPLE"))

        hex_code = f"""
        hex_r = RegularPolygon(n=6, color={r_col}, stroke_width=3)
        hex_r.scale(0.85)
        hex_r.move_to([-2.8, -0.2, 0])
        lbl_r = Text("{r_sym}", font_size=32, color=WHITE)
        lbl_r.move_to([-2.8, -0.2, 0])
        grp_r = MathTex(r"{r_grp}", font_size=30, color=GREEN)
        grp_r.next_to(hex_r, UP, buff=0.2)

        hex_p = RegularPolygon(n=6, color={p_col}, stroke_width=3)
        hex_p.scale(0.85)
        hex_p.move_to([2.8, -0.2, 0])
        lbl_p = Text("{p_sym}", font_size=32, color=WHITE)
        lbl_p.move_to([2.8, -0.2, 0])
        grp_p = MathTex(r"{p_grp}", font_size=30, color=GREEN)
        grp_p.next_to(hex_p, UP, buff=0.2)

        arrow = Arrow([-1.2, -0.2, 0], [1.2, -0.2, 0], color=WHITE, stroke_width=4, buff=0)
        cond_lbl = Text("{cond_safe}", font_size=20, color=WHITE)
        cond_lbl.next_to(arrow, DOWN, buff=0.15)
        temp_lbl = Text("{temp_safe}", font_size=20, color=BLUE)
        temp_lbl.next_to(cond_lbl, DOWN, buff=0.1)

        self.play(Create(hex_r), Write(lbl_r), Write(grp_r))
        self.wait(0.4)
        self.play(Create(arrow), Write(cond_lbl), Write(temp_lbl))
        self.wait(0.4)
        self.play(Create(hex_p), Write(lbl_p), Write(grp_p))
"""

    # Full equation at bottom (if provided)
    eq_repr = repr(sanitize_formula_tex(full_equation)) if full_equation else None
    eq_code = ""
    if eq_repr:
        eq_code = f"""
        eq = MathTex({eq_repr}, font_size=28, color=WHITE)
        eq.scale_to_fit_width(12.0)
        eq.move_to([0, -2.6, 0])
        self.play(Write(eq), run_time=1.5)
"""

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
        # Watermark
        watermark = Text("VidhyaGPT", font_size=18, color=GRAY)
        watermark.to_corner(DR, buff=0.2)
        self.add(watermark)

        # Heading
        heading = Text("{heading_safe}", font_size=32, color=YELLOW)
        heading.to_edge(UP, buff=0.3)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)

{hex_code}
{eq_code}
        self.wait({max(duration - 6.0, 0.5):.1f})
        self.play(FadeOut(VGroup(*self.mobjects)))
'''


def _make_projectile_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    wait = max(0.5, duration - 6.0)
    watermark_code = _get_watermark_code()

    return f'''from manim import *
import numpy as np

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)

        # Ground line
        ground = Line(LEFT * 5, RIGHT * 5, color=WHITE, stroke_width=2)
        ground.move_to(DOWN * 2)
        self.play(Create(ground), run_time=0.3)

        # Projectile path (parabola)
        path = ParametricFunction(
            lambda t: np.array([t - 3, -0.25 * (t - 3) ** 2 + 2 - 2, 0]),
            t_range=[0, 6],
            color=YELLOW, stroke_width=3,
        )
        path.move_to(DOWN * 0.5)
        self.play(Create(path), run_time=2.0)

        # Labels
        launch = Text("Launch", font_size=18, color=GREEN).move_to(LEFT * 3 + DOWN * 1.5)
        peak = Text("Maximum Height", font_size=18, color=RED).move_to(UP * 0.5)
        landing = Text("Landing", font_size=18, color=GREEN).move_to(RIGHT * 3 + DOWN * 1.5)
        self.play(FadeIn(launch), FadeIn(peak), FadeIn(landing), run_time=0.8)

        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def _make_circuit_diagram(class_name: str, heading: str, labels: list[str], duration: float) -> str:
    wait = max(0.5, duration - 5.5)
    watermark_code = _get_watermark_code()

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        heading = Text("{heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)

        # Simple circuit — battery + resistor + connecting wires
        # Battery
        batt = VGroup(
            Line(UP * 0.3, DOWN * 0.3, color=WHITE, stroke_width=3),
            Line(UP * 0.15, DOWN * 0.15, color=WHITE, stroke_width=3).shift(RIGHT * 0.15),
        ).move_to(LEFT * 3)
        b_label = Text("Battery", font_size=18, color=YELLOW).next_to(batt, DOWN, buff=0.3)

        # Resistor (zig-zag)
        resistor = VGroup(
            Line(LEFT * 0.5, LEFT * 0.3, color=WHITE),
            Line(LEFT * 0.3, LEFT * 0.15 + UP * 0.2, color=WHITE),
            Line(LEFT * 0.15 + UP * 0.2, RIGHT * 0.0 + DOWN * 0.2, color=WHITE),
            Line(RIGHT * 0.0 + DOWN * 0.2, RIGHT * 0.15 + UP * 0.2, color=WHITE),
            Line(RIGHT * 0.15 + UP * 0.2, RIGHT * 0.3, color=WHITE),
            Line(RIGHT * 0.3, RIGHT * 0.5, color=WHITE),
        ).move_to(RIGHT * 3)
        r_label = Text("Resistor", font_size=18, color=RED).next_to(resistor, DOWN, buff=0.3)

        # Wires
        wire_top = Line(batt.get_top() + UP * 0.1, resistor.get_top() + UP * 0.1, color=BLUE)
        wire_bot = Line(batt.get_bottom() + DOWN * 0.1, resistor.get_bottom() + DOWN * 0.1, color=BLUE)

        circuit = VGroup(batt, b_label, resistor, r_label, wire_top, wire_bot)
        circuit.move_to(DOWN * 0.3)

        self.play(Create(circuit), run_time=2.0)

        self.wait({wait:.1f})
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def make_example_scene(class_name: str, heading: str, steps: list[str], duration: float) -> str:
    safe_heading = _safe(heading, 40)
    step_lines = [_safe(s, 55) for s in steps[:4]]
    n = len(step_lines)
    anim_time = 1.0 + n * 0.8 + 1.5 + 0.5
    wait = max(0.5, duration - anim_time - 0.7)
    watermark_code = _get_watermark_code()
    clamp_code = _get_content_clamp_code("steps_group")

    steps_code = ""
    for i, s in enumerate(step_lines):
        steps_code += f'''
        s{i} = Text("{s}", font_size=24, color=WHITE)'''

    arrange_items = ", ".join(f"s{i}" for i in range(n))

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Heading — always at top
        heading = Text("{safe_heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)
{steps_code}

        # Arrange steps with spacing, centered in content zone
        steps_group = VGroup({arrange_items})
        steps_group.arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        steps_group.scale_to_fit_width(min(steps_group.width, 10.5))
        steps_group.move_to(ORIGIN + DOWN * 0.2)
{clamp_code}
        for s in steps_group:
            self.play(Write(s), run_time=0.8)

        # Highlight box around all steps
        box = SurroundingRectangle(steps_group, color=GREEN, buff=0.3)
        self.play(Create(box), run_time=0.7)

        self.wait({wait:.1f})

        # Clear everything
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


def make_summary_scene(class_name: str, heading: str, points: list[str], duration: float) -> str:
    safe_heading = _safe(heading, 40)
    point_lines = [_safe(p, 55) for p in points[:4]]
    n = len(point_lines)
    anim_time = 1.0 + n * 0.6 + 1.0 + 0.5
    wait = max(0.5, duration - anim_time - 0.7)
    watermark_code = _get_watermark_code()
    clamp_code = _get_content_clamp_code("pts")

    points_code = ""
    for i, p in enumerate(point_lines):
        points_code += f'''
        p{i} = Text("✓ {p}", font_size=26, color=GREEN)'''

    arrange_items = ", ".join(f"p{i}" for i in range(n))

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
{watermark_code}
        # Heading — always at top
        heading = Text("{safe_heading}", font_size=36, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)
{points_code}

        # Arrange points with spacing, centered in content zone
        pts = VGroup({arrange_items})
        pts.arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        pts.scale_to_fit_width(min(pts.width, 10.5))
        pts.move_to(ORIGIN + DOWN * 0.2)
{clamp_code}
        for p in pts:
            self.play(FadeIn(p, shift=RIGHT * 0.4), run_time=0.6)

        self.wait({wait:.1f})

        # Clear everything
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.7)
'''


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE DISPATCHER
# ═══════════════════════════════════════════════════════════════════

TEMPLATE_MAP = {
    "intro": lambda cn, content, dur: make_greeting_scene(
        cn,
        content.get("heading", content.get("title", "")),
        content.get("subtitle", ""),
        dur,
    ),
    "greeting": lambda cn, content, dur: make_greeting_scene(
        cn,
        content.get("heading", content.get("title", "")),
        content.get("subtitle", ""),
        dur,
    ),
    "bullets": lambda cn, content, dur: make_bullets_scene(
        cn,
        content.get("heading", ""),
        content.get("bullets", []),
        dur,
    ),
    "formula": lambda cn, content, dur: make_formula_scene(
        cn,
        content.get("heading", ""),
        content.get("formula_tex", ""),
        content.get("explanation", []),
        dur,
    ),
    "derivation": lambda cn, content, dur: make_derivation_scene(
        cn,
        content.get("heading", ""),
        content.get("steps", []),
        dur,
    ),
    "graph": lambda cn, content, dur: make_graph_scene(
        cn,
        content.get("heading", ""),
        content,
        dur,
    ),
    "diagram": lambda cn, content, dur: make_diagram_scene(
        cn,
        content.get("heading", ""),
        content.get("diagram_type", "generic"),
        content.get("labels", []),
        dur,
    ),
    "reaction": lambda cn, content, dur: make_reaction_diagram(
        cn,
        content.get("heading", ""),
        content.get("reactants", []),
        content.get("products", []),
        content.get("conditions", ""),
        dur,
        catalyst=content.get("catalyst", ""),
        temp_condition=content.get("temp_condition", ""),
        full_equation=content.get("full_equation", ""),
        intermediate=content.get("intermediate", None),
    ),
    "example": lambda cn, content, dur: make_example_scene(
        cn,
        content.get("heading", "Example"),
        content.get("steps", []),
        dur,
    ),
    "summary": lambda cn, content, dur: make_summary_scene(
        cn,
        content.get("heading", "Key Takeaways"),
        content.get("points", []),
        dur,
    ),
}


# ═══════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════

def validate_manim_code(code: str) -> tuple[bool, str]:
    """Validate generated Manim code before rendering."""
    BLOCKED = [
        "import os", "import sys", "subprocess", "open(",
        "exec(", "eval(", "ImageMobject", "SVGMobject", "__import__",
    ]
    ALLOWED_IMPORTS = {"import math"}
    for b in BLOCKED:
        if b in code and b not in ALLOWED_IMPORTS:
            return False, f"Blocked pattern: {b}"

    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"

    if "class Scene" not in code and "class " not in code:
        return False, "No Scene class found"

    ALLOWED_ANIMATIONS = {
        "Write", "Create", "FadeIn", "FadeOut", "Transform",
        "ReplacementTransform", "GrowFromCenter", "DrawBorderThenFill",
        "MoveAlongPath", "AnimationGroup", "LaggedStart", "Succession",
        "Wait", "ShrinkToCenter", "Indicate", "Uncreate",
    }

    play_calls = re.findall(r"self\.play\(([^)]+)\)", code)
    for call in play_calls:
        first_token = call.strip().split("(")[0].strip()
        # Handle comma-separated args like FadeOut(a), FadeOut(b)
        if "," in first_token:
            first_token = first_token.split(",")[0].strip().split("(")[0].strip()
        if (
            first_token
            and first_token[0].isupper()
            and first_token not in ALLOWED_ANIMATIONS
        ):
            return False, f"self.play() called with non-animation: {first_token}"

    return True, ""


# ═══════════════════════════════════════════════════════════════════
# OVERLAP PREVENTION — master check + auto-fix
# ═══════════════════════════════════════════════════════════════════

def check_no_overlap_risk(code: str) -> tuple[bool, str]:
    """
    Catches common overlap patterns BEFORE rendering.
    Returns (safe, warning_message).
    """
    issues = []

    # Check for multiple ORIGIN placements (objects stacking)
    origin_count = code.count("move_to(ORIGIN)")
    if origin_count > 1:
        issues.append(f"Multiple move_to(ORIGIN) calls ({origin_count})")

    # Check for VGroup without scale_to_fit_width
    if "VGroup(" in code and "scale_to_fit_width" not in code:
        issues.append("VGroup without scale_to_fit_width — may overflow screen")

    # Check for objects placed below visible area
    down_values = re.findall(r"DOWN \* ([\d.]+)", code)
    for v in down_values:
        if float(v) > 3.5:
            issues.append(f"Object at DOWN * {v} — may be off screen")

    if issues:
        return False, " | ".join(issues)
    return True, ""


def _auto_fix_overlap(code: str) -> str:
    """
    Automatically fix common overlap patterns in generated Manim code.
    Called when check_no_overlap_risk returns False.
    """
    # Fix 1: Replace multiple move_to(ORIGIN) — keep first, offset subsequent ones
    origin_count = code.count("move_to(ORIGIN)")
    if origin_count > 1:
        first_found = False
        lines = code.split('\n')
        offset = 0.5
        new_lines = []
        for line in lines:
            if "move_to(ORIGIN)" in line:
                if not first_found:
                    first_found = True
                    new_lines.append(line)
                else:
                    new_lines.append(line.replace("move_to(ORIGIN)", f"move_to(DOWN * {offset:.1f})"))
                    offset += 0.7
            else:
                new_lines.append(line)
        code = '\n'.join(new_lines)

    # Fix 2: Clamp all DOWN * N where N > 3.2 to DOWN * 2.5
    def clamp_down(match):
        val = float(match.group(1))
        if val > 3.2:
            return "DOWN * 2.5"
        return match.group(0)

    code = re.sub(r"DOWN \* ([\d.]+)", clamp_down, code)

    # Fix 3: Add scale_to_fit_width after VGroup.arrange if missing
    if "VGroup(" in code and "scale_to_fit_width" not in code:
        code = code.replace(
            ".arrange(DOWN,",
            ".arrange(DOWN,"
        )  # Can't blindly insert — templates already have it

    return code


# ═══════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def _split_narration_to_chunks(narration: str, max_chars: int = 55) -> list[str]:
    """Split narration into display chunks (max max_chars each)."""
    words = narration.split()
    chunks = []
    current = ""
    for word in words:
        if len(current + " " + word) <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks[:4]


def make_safe_fallback(class_name: str, scene_title: str, narration: str, duration: float) -> str:
    """
    Last resort fallback. Uses actual scene title and narration text.
    Never uses generic placeholder text.
    """
    title_safe = scene_title.replace('"', "'")[:50]
    chunks = _split_narration_to_chunks(narration)

    chunk_lines = []
    for c in chunks:
        safe_c = c.replace('"', "'")
        chunk_lines.append(f'        Text("{safe_c}", font_size=28, color=WHITE),')
    chunk_code = "\n".join(chunk_lines)

    n = len(chunks)
    anim_time = 1.0 + n * 0.8 + 0.5
    wait = max(duration - anim_time, 0.3)

    return f'''from manim import *

class {class_name}(Scene):
    def construct(self):
        watermark = Text("VidhyaGPT", font_size=18, color=GRAY)
        watermark.to_corner(DR, buff=0.2)
        self.add(watermark)

        heading = Text("{title_safe}", font_size=34, color=YELLOW)
        heading.to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=0.8)
        self.wait(0.2)

        content = VGroup(
{chunk_code}
        )
        content.arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        content.scale_to_fit_width(11.0)
        content.move_to(ORIGIN + DOWN * 0.2)
        if content.get_bottom()[1] < -2.8:
            content.shift(UP * (abs(content.get_bottom()[1]) - 2.8 + 0.2))

        for item in content:
            self.play(FadeIn(item, shift=RIGHT * 0.2), run_time=0.5)
            self.wait(0.3)

        self.wait({wait:.1f})
        self.play(FadeOut(VGroup(*self.mobjects)))
'''


# ── GPT-4o extraction helpers ────────────────────────────────────────

async def _extract_bullets_from_narration(narration: str, topic: str) -> list[str]:
    """Extract 3-4 key bullet points from narration using GPT-4o."""
    if not _HAS_OPENAI:
        return _split_narration_to_chunks(narration)
    try:
        result = await generate_with_gpt4(
            system_prompt="""Extract 3-4 key bullet points from the narration.
Return JSON: {"bullets": ["short point 1", "short point 2", "short point 3"]}
Each bullet: max 7 words, no generic phrases like 'key concepts' or 'important details'.
Must be specific to the actual content.""",
            user_prompt=f"Topic: {topic}\nNarration: {narration}",
            json_mode=True
        )
        data = json.loads(result)
        bullets = data.get("bullets", [])
        return bullets[:4] if bullets else _split_narration_to_chunks(narration)
    except Exception as exc:
        LOGGER.warning("GPT-4o bullet extraction failed: %s", exc)
        return _split_narration_to_chunks(narration)


async def _extract_formula_from_narration(narration: str, topic: str, subject: str) -> dict:
    """Extract LaTeX formula and explanation from narration using GPT-4o."""
    if not _HAS_OPENAI:
        return {"formula_tex": "", "explanation": []}
    try:
        result = await generate_with_gpt4(
            system_prompt="""Extract the mathematical/chemical formula from the narration.
Return JSON:
{
  "formula_tex": "LaTeX formula e.g. F = \\\\frac{GMm}{r^2}",
  "explanation": ["F = Force (N)", "G = Gravitational Constant", ...]
}
If no formula exists in narration, return: {"formula_tex": "", "explanation": []}
IMPORTANT: The formula MUST be from the narration, never make one up.""",
            user_prompt=f"Topic: {topic}\nSubject: {subject}\nNarration: {narration}",
            json_mode=True
        )
        return json.loads(result)
    except Exception as exc:
        LOGGER.warning("GPT-4o formula extraction failed: %s", exc)
        return {"formula_tex": "", "explanation": []}


async def _extract_reaction_content(narration: str, topic: str) -> dict:
    """Extract reaction diagram content from narration using GPT-4o."""
    if not _HAS_OPENAI:
        return {}
    try:
        result = await generate_with_gpt4(
            system_prompt="""Extract chemical reaction information for a diagram.
Return JSON:
{
  "heading": "reaction step name",
  "reactants": [{"symbol": "Ar", "group": "NH_2", "color": "ORANGE"}],
  "products": [{"symbol": "Ar", "group": "CHO", "color": "PURPLE"}],
  "conditions": "CHCl3 + NaOH",
  "temp_condition": "temperature if any",
  "catalyst": "catalyst if any",
  "full_equation": "balanced equation in LaTeX"
}
Colors: ORANGE=starting material, PURPLE=intermediate, BLUE=final product.
If you cannot extract a reaction, return empty {}.""",
            user_prompt=f"Topic: {topic}\nNarration: {narration}",
            json_mode=True
        )
        return json.loads(result)
    except Exception as exc:
        LOGGER.warning("GPT-4o reaction extraction failed: %s", exc)
        return {}


async def _extract_example_steps(narration: str, topic: str, subject: str) -> list[str]:
    """Extract real numerical example steps from narration using GPT-4o."""
    if not _HAS_OPENAI:
        return _split_narration_to_chunks(narration)
    try:
        result = await generate_with_gpt4(
            system_prompt="""Extract step-by-step solution from narration.
Return JSON: {"steps": ["Step 1: actual calculation", "Step 2: ...", "Answer: ..."]}
Each step must contain REAL values and calculations, not generic placeholders.
Max 5 steps, max 50 chars each.
If there are no real numerical steps, return: {"steps": []}""",
            user_prompt=f"Topic: {topic}\nSubject: {subject}\nNarration: {narration}",
            json_mode=True
        )
        data = json.loads(result)
        steps = data.get("steps", [])
        return steps[:5] if steps else _split_narration_to_chunks(narration)
    except Exception as exc:
        LOGGER.warning("GPT-4o example extraction failed: %s", exc)
        return _split_narration_to_chunks(narration)


async def _extract_summary_points(narration: str, topic: str) -> list[str]:
    """Extract real summary points from narration using GPT-4o."""
    if not _HAS_OPENAI:
        return _split_narration_to_chunks(narration)
    try:
        result = await generate_with_gpt4(
            system_prompt="""Extract 3-4 key takeaways from narration.
Return JSON: {"points": ["specific fact 1", "specific fact 2", ...]}
Must be SPECIFIC to the topic, not generic phrases like 'understand key concepts'.
Max 8 words each.""",
            user_prompt=f"Topic: {topic}\nNarration: {narration}",
            json_mode=True
        )
        data = json.loads(result)
        points = data.get("points", [])
        return points[:4] if points else _split_narration_to_chunks(narration)
    except Exception as exc:
        LOGGER.warning("GPT-4o summary extraction failed: %s", exc)
        return _split_narration_to_chunks(narration)


def _detect_diagram_type(topic: str, narration: str, subject: str) -> str:
    """Auto-detect diagram type from topic and narration."""
    combined = (topic + " " + narration).lower()

    if any(w in combined for w in ["orbit", "planet", "kepler", "satellite", "ellipse"]):
        return "orbit"
    if any(w in combined for w in ["force", "friction", "tension", "newton", "push", "pull"]):
        return "force"
    if any(w in combined for w in ["wave", "sound", "frequency", "wavelength", "amplitude"]):
        return "wave"
    if any(w in combined for w in ["atom", "electron", "nucleus", "bohr", "shell"]):
        return "atom"
    if any(w in combined for w in ["mirror", "lens", "refraction", "reflection", "ray"]):
        return "ray"
    if any(w in combined for w in ["projectile", "trajectory"]):
        return "projectile"
    if any(w in combined for w in ["circuit", "resistance", "current", "battery", "bulb"]):
        return "circuit"
    if any(w in combined for w in ["triangle", "circle", "polygon", "angle", "pythagoras"]):
        return "geometry"
    if any(w in combined for w in ["graph", "function", "curve", "parabola", "coordinate"]):
        return "graph"

    return "generic"


def _is_generic_content(items: list[str]) -> bool:
    """Check if a list of strings contains generic placeholder text."""
    generic_phrases = [
        "key relationships", "practical application", "step-by-step process",
        "key term definitions", "common applications", "exam-relevant",
        "identifying the given values", "apply the concept",
        "calculate the result", "the final answer",
        "understand the key concepts", "practice with real",
        "we learned about", "we learn about",
        "visual overview", "important connections",
        "reaction overview", "key reactants and products", "conditions required",
        "trend overview", "key data points", "pattern analysis",
        "important details", "review this topic",
        "key concept", "point 1", "point 2", "point 3",
        "step 1: read", "step 2: apply", "step 3: calculate",
        "remember the formula", "practice daily", "you are doing great",
        "object a", "object b", "component a", "component b",
    ]
    for item in items:
        if any(g in item.lower() for g in generic_phrases):
            return True
    return False


async def generate_manim_code(
    scene_number: int,
    scene_title: str,
    narration: str,
    visual_content: dict,
    duration: float,
    topic: str,
    subject: str,
    scene_type: str = "bullets",
    max_retries: int = 2,
) -> str:
    """
    Generate Manim code for one scene using HARDCODED TEMPLATES.

    Priority for content:
    1. Use visual_content from the script JSON (best — already structured)
    2. Fall back to GPT-4o extraction from narration (if visual_content missing)
    3. Fall back to safe narration-based rendering (if GPT-4o fails too)
    """
    class_name = f"Scene{scene_number}"
    content = visual_content if isinstance(visual_content, dict) and visual_content else {}

    LOGGER.info("Scene %d: type=%s, content_keys=%s",
                scene_number, scene_type, list(content.keys()) if content else [])

    # Normalize scene_type
    st_map = {
        "concept": "bullets", "equation": "formula",
        "goodbye": "summary", "plot": "graph", "chart": "graph",
        "derive": "derivation", "proof": "derivation",
        "application": "bullets", "applications": "bullets",
    }
    scene_type = st_map.get(scene_type, scene_type)

    # Handle diagram with reaction sub-type
    if scene_type == "diagram" and content.get("diagram_type") == "reaction":
        scene_type = "reaction"

    # ── Route based on scene_type ──────────────────────────────────

    if scene_type in ("intro", "greeting"):
        code = make_greeting_scene(
            class_name,
            content.get("heading", topic[:40]),
            content.get("subtitle", ""),
            duration
        )

    elif scene_type == "bullets":
        bullets = content.get("bullets", [])
        if not bullets or _is_generic_content(bullets):
            bullets = await _extract_bullets_from_narration(narration, topic)
        code = make_bullets_scene(
            class_name,
            content.get("heading", scene_title[:40]),
            bullets,
            duration
        )

    elif scene_type == "formula":
        formula_tex = content.get("formula_tex", "")
        explanation = content.get("explanation", [])

        if not formula_tex or not formula_tex.strip():
            LOGGER.info("Scene %d: no formula in visual_content, trying GPT-4o extraction", scene_number)
            extracted = await _extract_formula_from_narration(narration, topic, subject)
            formula_tex = extracted.get("formula_tex", "")
            explanation = extracted.get("explanation", explanation)

        if not formula_tex or not formula_tex.strip():
            LOGGER.warning("Scene %d: no formula found → safe fallback", scene_number)
            code = make_safe_fallback(class_name, scene_title, narration, duration)
        else:
            code = make_formula_scene(
                class_name,
                content.get("heading", scene_title[:40]),
                formula_tex,
                explanation,
                duration
            )

    elif scene_type == "diagram":
        diagram_type = content.get("diagram_type", "")
        labels = content.get("labels", [])

        if not diagram_type or diagram_type == "generic":
            diagram_type = _detect_diagram_type(topic, narration, subject)

        if _is_generic_content(labels):
            labels = []

        if diagram_type == "generic":
            LOGGER.warning("Scene %d: no diagram type detected → safe fallback", scene_number)
            bullets = await _extract_bullets_from_narration(narration, topic)
            code = make_bullets_scene(class_name, scene_title[:40], bullets, duration)
        else:
            code = make_diagram_scene(
                class_name,
                content.get("heading", scene_title[:40]),
                diagram_type,
                labels,
                duration
            )

    elif scene_type == "reaction":
        reactants = content.get("reactants", [])
        products = content.get("products", [])

        has_real = bool(reactants and products)
        if has_real:
            r_sym = reactants[0].get("symbol", "") if reactants else ""
            p_sym = products[0].get("symbol", "") if products else ""
            if r_sym in ("", "A") and p_sym in ("", "B"):
                has_real = False

        if not has_real:
            LOGGER.info("Scene %d: no real reaction data, trying GPT-4o extraction", scene_number)
            extracted = await _extract_reaction_content(narration, topic)
            if extracted.get("reactants") and extracted.get("products"):
                content = {**content, **extracted}
                reactants = content.get("reactants", [])
                products = content.get("products", [])
                has_real = True

        if not has_real:
            LOGGER.warning("Scene %d: reaction extraction failed → safe fallback", scene_number)
            code = make_safe_fallback(class_name, scene_title, narration, duration)
        else:
            code = make_reaction_diagram(
                class_name,
                content.get("heading", scene_title[:40]),
                reactants,
                products,
                content.get("conditions", ""),
                duration,
                catalyst=content.get("catalyst", ""),
                temp_condition=content.get("temp_condition", ""),
                full_equation=content.get("full_equation", ""),
                intermediate=content.get("intermediate", None),
            )

    elif scene_type == "example":
        steps = content.get("steps", [])

        if not steps or _is_generic_content(steps):
            steps = await _extract_example_steps(narration, topic, subject)

        if not steps or _is_generic_content(steps):
            code = make_safe_fallback(class_name, scene_title, narration, duration)
        else:
            code = make_example_scene(
                class_name,
                content.get("heading", "Example"),
                steps,
                duration
            )

    elif scene_type == "summary":
        points = content.get("points", [])

        if not points or _is_generic_content(points):
            points = await _extract_summary_points(narration, topic)

        code = make_summary_scene(
            class_name,
            content.get("heading", "Key Takeaways"),
            points,
            duration
        )

    elif scene_type == "derivation":
        steps = content.get("steps", [])
        if not steps:
            steps = _split_narration_to_chunks(narration)
        code = make_derivation_scene(
            class_name,
            content.get("heading", scene_title[:40]),
            steps,
            duration
        )

    elif scene_type == "graph":
        if not content or content.get("function", "x") == "x":
            bullets = await _extract_bullets_from_narration(narration, topic)
            code = make_bullets_scene(class_name, scene_title[:40], bullets, duration)
        else:
            code = make_graph_scene(
                class_name,
                content.get("heading", "Graph"),
                content,
                duration
            )

    else:
        code = make_safe_fallback(class_name, scene_title, narration, duration)

    # Validate syntax + security
    is_valid, error = validate_manim_code(code)
    if not is_valid:
        LOGGER.warning("Scene %d template code invalid: %s. Using safe fallback.", scene_number, error)
        code = make_safe_fallback(class_name, scene_title, narration, duration)

    # Overlap prevention check + auto-fix
    overlap_safe, overlap_warning = check_no_overlap_risk(code)
    if not overlap_safe:
        LOGGER.warning("Scene %d overlap risk detected: %s. Auto-fixing...", scene_number, overlap_warning)
        code = _auto_fix_overlap(code)
        is_valid2, error2 = validate_manim_code(code)
        if not is_valid2:
            LOGGER.warning("Scene %d auto-fix broke syntax: %s. Using safe fallback.", scene_number, error2)
            code = make_safe_fallback(class_name, scene_title, narration, duration)

    LOGGER.info("Scene %d Manim code generated (%d chars, type=%s)", scene_number, len(code), scene_type)
    return code

