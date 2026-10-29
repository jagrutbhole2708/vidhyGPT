"""
Script generator — produces 6-scene narration + visual_content JSON using OpenAI GPT-4o.
scene_type must be one of: intro, bullets, formula, diagram, example, summary, reaction

CORE PRINCIPLE — LESS ON SCREEN, MORE IN VOICE:
  narration  = what the teacher SAYS aloud (full explanation, 40-70 words)
  visual_content = what appears ON SCREEN (key terms, formulas, labels — NOT repeated narration)

Subject-aware: generates different flows for Physics, Chemistry, Mathematics.
"""

import asyncio
import json
import logging
import os
import re

from dotenv import load_dotenv
from video.openai_client import OpenAIClientError, generate_json

load_dotenv()
LOGGER = logging.getLogger(__name__)

VALID_SCENE_TYPES = {"intro", "greeting", "bullets", "formula", "derivation", "graph", "diagram", "example", "summary", "reaction"}


# ═══════════════════════════════════════════════════════════════════
# TITLE CLEANING — converts raw question into clean video title
# ═══════════════════════════════════════════════════════════════════

def clean_topic_title(raw_question: str) -> str:
    """
    Convert user question into a clean video title.
    "explain me newtons law of motion" → "Newton's Law of Motion"
    "what is sandmeyer reaction?" → "Sandmeyer Reaction"
    "how does photosynthesis work" → "Photosynthesis"
    """
    # Remove common question prefixes
    prefixes_to_remove = [
        r"^explain\s+me\s+",
        r"^explain\s+",
        r"^what\s+is\s+",
        r"^what\s+are\s+",
        r"^how\s+does\s+",
        r"^how\s+do\s+",
        r"^tell\s+me\s+about\s+",
        r"^describe\s+",
        r"^define\s+",
        r"^derive\s+",
        r"^solve\s+",
        r"^find\s+",
        r"^prove\s+",
        r"^i\s+want\s+to\s+know\s+about\s+",
        r"^can\s+you\s+explain\s+",
        r"^please\s+explain\s+",
        r"^teach\s+me\s+about\s+",
        r"^teach\s+me\s+",
    ]

    title = raw_question.strip().rstrip("?").rstrip(".")

    for prefix in prefixes_to_remove:
        title = re.sub(prefix, "", title, flags=re.IGNORECASE).strip()

    # Title case
    title = title.title()

    # Fix common title case issues
    minor_words = {"Of", "The", "A", "An", "And", "Or", "But", "In", "On", "At", "To", "For", "Is", "By", "With"}
    words = title.split()
    result = []
    for i, word in enumerate(words):
        if i == 0:
            result.append(word)  # always capitalize first word
        elif word in minor_words:
            result.append(word.lower())
        else:
            result.append(word)

    return " ".join(result)


# ═══════════════════════════════════════════════════════════════════
# SUBJECT-SPECIFIC 6-SCENE PROMPTS
# ═══════════════════════════════════════════════════════════════════

def get_script_prompt(subject: str, clean_title: str) -> str:
    """Returns subject-specific script generation prompt with 6-scene flow."""

    base = f"""
You are scripting an educational video for Indian school students (NCERT CBSE).
The video title is: "{clean_title}"

Return ONLY valid JSON. No markdown. No text outside JSON.

JSON structure:
{{
  "title": "{clean_title}",
  "scenes": [
    {{
      "scene_number": 1,
      "scene_type": "intro|bullets|formula|diagram|example|summary|reaction",
      "title": "short scene title",
      "narration": "what the voice says — full explanation here",
      "visual_content": {{ depends on scene_type }}
    }}
  ]
}}

## CORE PRINCIPLE — LESS ON SCREEN, MORE IN VOICE:
The NARRATION is where you explain everything in detail.
The VISUAL shows only: key terms, formulas, diagrams, important labels.
NEVER put long sentences on screen. Screen shows structure. Voice explains.

Example:
  Narration: "Gravity is the force that pulls every object with mass towards every other object. The more massive an object is, the stronger its gravitational pull. This is why the Earth pulls us down but we barely affect the Earth."
  Visual: bullets = ["Force between masses", "Increases with mass", "Decreases with distance"]

## NARRATION RULES:
- 40-70 words per scene (15-25 seconds of natural speech)
- Write as a knowledgeable, warm teacher explaining to a student
- Explain the WHY, not just the WHAT
- Use analogies: "Think of it like...", "Imagine you are..."
- Reference the visual: "As you can see here...", "Notice how..."
- NO question phrasing, NO "Hello students"
- First scene ALWAYS starts: "In this video, we explore {clean_title}."

## visual_content per scene_type:
  intro:    {{"heading": "{clean_title}", "subtitle": "one short descriptive line"}}
  bullets:  {{"heading": "...", "bullets": ["short term or phrase", ...] }}  ← max 4, max 6 words each
  formula:  {{"heading": "...", "formula_tex": "LaTeX", "explanation": ["var = meaning (unit)"]}}
  diagram:  {{"heading": "...", "diagram_type": "orbit|force|wave|atom|ray|geometry|projectile|circuit", "labels": [...]}}
  reaction: {{"heading": "...", "diagram_type": "reaction", "reactants": [...], "products": [...], "conditions": "...", "full_equation": "..."}}
  example:  {{"heading": "Example", "steps": ["Step 1: value", "Step 2: value", "= answer"]}}
  summary:  {{"heading": "Key Points", "points": ["short point", ...] }}  ← max 4, max 8 words each
"""

    physics_flow = f"""
## PHYSICS VIDEO FLOW (6 scenes):
Scene 1 (intro):    "In this video, we explore {clean_title}." + what student will understand
Scene 2 (bullets):  What is it? Core concept in simple terms
Scene 3 (diagram):  Visual representation — orbit/force/wave/ray/atom as appropriate
Scene 4 (formula):  The key mathematical formula — MUST use MathTex LaTeX
Scene 5 (example):  One numerical example solved step by step
Scene 6 (summary):  3-4 key takeaways as bullet points

Diagram rules for Physics:
- Motion, orbits, Kepler → diagram_type: "orbit"
- Force, friction, Newton's laws → diagram_type: "force"
- Waves, sound, light → diagram_type: "wave"
- Optics, mirrors, lenses → diagram_type: "ray"
- Atoms, nucleus → diagram_type: "atom"
- Projectile motion → diagram_type: "projectile"

Formula LaTeX (double backslash in JSON):
  Newton F=ma:       "F = ma"
  Gravity:           "F = \\\\frac{{GMm}}{{r^2}}"
  Kinetic energy:    "KE = \\\\frac{{1}}{{2}}mv^2"
  Wave speed:        "v = f\\\\lambda"
  Equations motion:  "v^2 = u^2 + 2as"
  Ohm's law:         "V = IR"
"""

    chemistry_flow = f"""
## CHEMISTRY VIDEO FLOW (6 scenes):

For REACTION topics (Sandmeyer, Reimer-Tiemann, Aldol, Cannizzaro, etc.):
Scene 1 (intro):    "In this video, we explore {clean_title}." + what reaction does
Scene 2 (bullets):  What is this reaction/concept? Key characteristics (3-4 short points)
Scene 3 (reaction): Step 1 of reaction — show reactants → products with conditions
Scene 4 (formula):  Balanced chemical equation in LaTeX
Scene 5 (bullets):  Applications, variants, or key features (NOT a worked example)
Scene 6 (summary):  Key conditions, uses, and important points to remember

CRITICAL RULES FOR CHEMISTRY:
- NEVER use scene_type "example" for chemical reactions. Reactions are NOT numerical problems.
- Use scene_type "reaction" for showing reaction diagrams (with reactants, products, conditions).
- Use scene_type "bullets" for applications, variants, features.
- Scene 5 should be "bullets" with applications/variants, NOT a worked example.

Reaction visual_content format (REQUIRED for reaction scenes):
{{
  "diagram_type": "reaction",
  "heading": "Step Name",
  "reactants": [
    {{"symbol": "Ar", "group": "NH_2", "color": "ORANGE"}}
  ],
  "products": [
    {{"symbol": "Ar", "group": "N_2^+", "color": "PURPLE"}}
  ],
  "conditions": "NaNO_2 + 2HX",
  "temp_condition": "0°C to 5°C",
  "catalyst": "CuX",
  "full_equation": "Ar-NH_2 + NaNO_2 + 2HX \\\\rightarrow Ar-N_2^+ X^- + NaX + 2H_2O"
}}

Color coding: ORANGE=starting material/reactant, PURPLE=intermediate/diazonium, BLUE=final product, GREEN=catalyst/conditions

For NON-REACTION chemistry topics (acids-bases, periodic table, bonding, etc.):
Scene 1 (intro):    "In this video, we explore {clean_title}."
Scene 2 (bullets):  Core concept definition + key points
Scene 3 (diagram):  Visual diagram (atom, molecule, periodic trend)
Scene 4 (formula):  Key formula or equation
Scene 5 (bullets):  Applications or real-world examples
Scene 6 (summary):  Key takeaways

Chemical formula LaTeX:
  Subscripts:   H_2O, CO_2, NaNO_2, H_2SO_4
  Superscripts: Ca^{{2+}}, Cl^-, N_2^+
  Arrow:        \\\\rightarrow
  Equilibrium:  \\\\rightleftharpoons
"""

    math_flow = f"""
## MATHEMATICS VIDEO FLOW (6 scenes):
Scene 1 (intro):    "In this video, we explore {clean_title}." + what theorem/concept we prove
Scene 2 (bullets):  Statement of the theorem/concept with key terms defined
Scene 3 (diagram):  Geometric figure or graph that illustrates the concept
Scene 4 (formula):  The main formula or expression using MathTex
Scene 5 (example):  Step-by-step numerical example — show working clearly
Scene 6 (summary):  Statement to remember + 2-3 key points

Diagram rules for Mathematics:
- Triangles, circles, polygons → diagram_type: "geometry"
- Functions, curves, graphs → diagram_type: "graph"
- Coordinate geometry → diagram_type: "graph" with axes

Formula LaTeX for Mathematics (double backslash in JSON):
  Quadratic:     "x = \\\\frac{{-b \\\\pm \\\\sqrt{{b^2 - 4ac}}}}{{2a}}"
  Pythagoras:    "a^2 + b^2 = c^2"
  Circle area:   "A = \\\\pi r^2"
  Derivative:    "\\\\frac{{d}}{{dx}}(x^n) = nx^{{n-1}}"
  Integration:   "\\\\int x^n dx = \\\\frac{{x^{{n+1}}}}{{n+1}} + C"
  Binomial:      "(a+b)^2 = a^2 + 2ab + b^2"
  AP sum:        "S_n = \\\\frac{{n}}{{2}}(2a + (n-1)d)"
"""

    flow_map = {
        "physics": physics_flow,
        "chemistry": chemistry_flow,
        "mathematics": math_flow,
        "general": physics_flow  # default to physics flow
    }

    return base + flow_map.get(subject.lower() if subject else "general", physics_flow)


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _fallback_enabled() -> bool:
    return os.getenv("VIDEO_ALLOW_LOCAL_SCRIPT_FALLBACK", "1").strip().lower() not in {"0", "false", "no"}


def _build_local_script(topic: str, context: str, subject: str, class_level: str) -> dict:
    """Local fallback script when LLM is unavailable — 6 scenes."""
    # Sanitize the context — strip ALL markdown/LaTeX before using in narration
    raw_hint = (context or "").strip()[:200]
    # Remove markdown formatting from hint
    hint = re.sub(r'#{1,6}\s*', '', raw_hint)
    hint = hint.replace('**', '').replace('__', '').replace('*', '').replace('_', ' ')
    hint = re.sub(r'\$\$.*?\$\$', '', hint, flags=re.DOTALL)
    hint = re.sub(r'\$.*?\$', '', hint)
    hint = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', hint)  # remove \text{...}, \frac{...}
    hint = re.sub(r'\\[a-zA-Z]+', '', hint)  # remove remaining LaTeX commands
    hint = re.sub(r'[{}]', '', hint)
    hint = re.sub(r'^\s*[-•>]\s*', '', hint, flags=re.MULTILINE)
    hint = re.sub(r'\s+', ' ', hint).strip()[:120]

    scenes = [
        {
            "scene_number": 1,
            "scene_type": "intro",
            "title": "Introduction",
            "narration": f"In this video, we explore {topic}. {hint}" if hint else f"In this video, we explore {topic}.",
            "visual_content": {
                "heading": topic[:40],
                "subtitle": ""
            }
        },
        {
            "scene_number": 2,
            "scene_type": "bullets",
            "title": f"Understanding {topic}"[:40],
            "narration": f"Let us understand the basics of {topic}. {hint}" if hint else f"Let us understand the basics of {topic}.",
            "visual_content": {
                "heading": f"Understanding {topic}"[:40]
            }
        },
        {
            "scene_number": 3,
            "scene_type": "bullets",
            "title": f"How {topic} Works"[:40],
            "narration": f"Now let us look at how {topic} works in practice.",
            "visual_content": {
                "heading": f"How {topic} Works"[:40]
            }
        },
        {
            "scene_number": 4,
            "scene_type": "bullets",
            "title": "Important Points",
            "narration": f"Here are the most important things to remember about {topic}.",
            "visual_content": {
                "heading": "Important Points"
            }
        },
        {
            "scene_number": 5,
            "scene_type": "bullets",
            "title": "Applications",
            "narration": f"Let us look at real-world applications of {topic}.",
            "visual_content": {
                "heading": "Applications"
            }
        },
        {
            "scene_number": 6,
            "scene_type": "summary",
            "title": "Key Takeaways",
            "narration": f"To summarize, we explored {topic} today. Keep practicing and revising these concepts.",
            "visual_content": {
                "heading": "Key Takeaways"
            }
        },
    ]

    # Sanitize all narrations
    for scene in scenes:
        if "narration" in scene:
            scene["narration"] = _sanitize_narration(scene["narration"])

    return {"title": topic, "scenes": scenes}


def _sanitize_narration(text: str) -> str:
    """Strip ALL markdown/LaTeX symbols from narration — it goes to TTS as speech."""
    # Remove markdown headings (###, ##, #)
    text = re.sub(r'#{1,6}\s*', '', text)
    # Remove bold/italic markers
    text = text.replace('**', '').replace('__', '').replace('*', '').replace('_', ' ')
    # Remove inline code backticks
    text = re.sub(r'`[^`]*`', '', text)
    # Remove LaTeX block equations entirely (they can't be spoken)
    text = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    text = re.sub(r'\$.*?\$', '', text)
    # Extract text from \text{...}, \textbf{...}, etc. (keep the content)
    text = re.sub(r'\\text(?:bf|rm|it|sf)?\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\mathbf\{([^}]*)\}', r'\1', text)
    # Remove remaining LaTeX commands (\frac, \rightarrow, etc.)
    text = re.sub(r'\\[a-zA-Z]+', ' ', text)
    # Remove curly braces
    text = re.sub(r'[{}]', '', text)
    # Remove subscript/superscript notation
    text = re.sub(r'[_^]', ' ', text)
    # Remove bullet markers at start of lines
    text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
    # Remove numbered list markers
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)
    # Remove blockquote markers
    text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _ensure_visual_content(scene: dict, topic: str) -> dict:
    """
    Ensure a scene has visual_content dict. If missing, set an empty one.
    The actual content extraction is handled downstream by generate_manim_code
    using GPT-4o extraction or safe narration-based fallback.

    RULE: Never inject generic placeholder text here.
    """
    if "visual_content" in scene and isinstance(scene["visual_content"], dict):
        return scene

    st = scene.get("scene_type", "bullets")
    title = scene.get("title", topic)

    if st in ("intro", "greeting"):
        scene["visual_content"] = {"heading": topic[:40], "subtitle": ""}
    elif st in ("formula", "derivation", "diagram", "reaction", "graph"):
        # Set empty visual_content — generate_manim_code will handle extraction
        scene["visual_content"] = {"heading": title[:40]}
        LOGGER.info("Scene '%s' (type=%s) has no visual_content — will be extracted downstream", title, st)
    elif st == "example":
        scene["visual_content"] = {"heading": title[:40]}
    elif st == "summary":
        scene["visual_content"] = {"heading": "Key Takeaways"}
    else:  # bullets or unknown
        scene["visual_content"] = {"heading": title[:40]}

    return scene


def _validate_script(parsed: dict, topic: str, subject: str = "general") -> dict:
    """Validate and fix the parsed script JSON with subject-aware corrections."""
    if not isinstance(parsed, dict) or "scenes" not in parsed:
        raise ValueError("Script response missing 'scenes' key")

    scenes = parsed["scenes"]
    if not isinstance(scenes, list) or len(scenes) == 0:
        raise ValueError("Script has no scenes")

    # Fix scene_types to valid ones
    expected_order = ["intro", "bullets", "diagram", "formula", "example", "summary"]
    for i, scene in enumerate(scenes):
        scene["scene_number"] = i + 1
        st = scene.get("scene_type", "").lower().strip()
        # Map alternative scene_types to valid ones
        type_map = {
            "concept": "bullets", "equation": "formula", "greeting": "intro",
            "goodbye": "summary", "plot": "graph", "chart": "graph",
            "derive": "derivation", "proof": "derivation",
            "application": "bullets", "applications": "bullets",
        }
        st = type_map.get(st, st)
        if st not in VALID_SCENE_TYPES:
            st = expected_order[i] if i < len(expected_order) else "bullets"
        scene["scene_type"] = st

        # Ensure visual_content exists
        _ensure_visual_content(scene, topic)

        # Sanitize narration — strip all markdown/LaTeX from speech
        if "narration" in scene:
            scene["narration"] = _sanitize_narration(scene["narration"])

    # ── Subject-specific validation ──────────────────────────────────
    scene_types = [s.get("scene_type") for s in scenes]
    title_lower = topic.lower()

    # Chemistry: reaction topics MUST have at least one reaction scene
    reaction_keywords = [
        "reaction", "synthesis", "mechanism", "reagent", "diazotization",
        "esterification", "saponification", "aldol", "cannizzaro", "reimer",
        "tiemann", "sandmeyer", "grignard", "friedel", "craft", "wittig",
        "beckmann", "kolbe", "wurtz", "haloform", "oxidation", "reduction",
    ]
    is_reaction_topic = (
        subject.lower() == "chemistry"
        and any(kw in title_lower for kw in reaction_keywords)
    )

    if is_reaction_topic:
        has_reaction = any(t == "reaction" for t in scene_types)
        if not has_reaction:
            LOGGER.warning("[script_validator] Chemistry reaction topic but no reaction scene — fixing scene 3")
            if len(scenes) >= 3:
                scenes[2]["scene_type"] = "reaction"
        # For chemistry: convert any "example" scene to "bullets" (reactions don't have worked examples)
        for s in scenes:
            if s["scene_type"] == "example":
                LOGGER.warning("[script_validator] Converting 'example' scene to 'bullets' for chemistry reaction topic")
                s["scene_type"] = "bullets"

    # Physics: should have formula and/or diagram
    if subject.lower() == "physics":
        has_formula = any(t == "formula" for t in scene_types)
        has_diagram = any(t == "diagram" for t in scene_types)
        if not has_formula and not has_diagram:
            LOGGER.warning("[script_validator] Physics topic but no formula or diagram — fixing")
            if len(scenes) >= 4:
                scenes[3]["scene_type"] = "formula"

    # Mathematics: should have formula
    if subject.lower() == "mathematics":
        has_formula = any(t == "formula" for t in scene_types)
        if not has_formula:
            LOGGER.warning("[script_validator] Math topic but no formula — fixing")
            if len(scenes) >= 4:
                scenes[3]["scene_type"] = "formula"

    parsed["scenes"] = scenes
    return parsed


async def generate_script(topic: str, context: str, subject: str, class_level: str) -> dict:
    """Generate a 6-scene video script using LLM with subject-specific prompt."""
    # Clean the topic title first
    clean_title = clean_topic_title(topic)

    # Use subject-aware prompt with clean title
    prompt = get_script_prompt(subject, clean_title)

    # Build user message with subject-specific instructions
    user_msg = f"""Topic to teach: {clean_title}
Subject: {subject}
Class: {class_level} (NCERT CBSE)
Context from NCERT textbook:
{context}

IMPORTANT REQUIREMENTS:
1. Video title must be exactly: "{clean_title}"
2. First scene narration must start: "In this video, we explore {clean_title}."
3. NO markdown in narration — narration is spoken by TTS (no ##, **, $$, \\text, etc.)
4. Each scene MUST have complete visual_content with all required fields.
5. Less text on screen, more explanation through voice.
"""

    # Add subject-specific instructions
    subj = (subject or "general").lower()
    if subj == "chemistry":
        user_msg += """
CHEMISTRY-SPECIFIC:
- If this is a chemical reaction topic: use scene_type "reaction" for at least one scene.
- Include actual reactants, products, conditions in visual_content.
- NEVER use scene_type "example" for reactions — reactions have no numerical examples.
- Scene 5 should be "bullets" with applications or variants.
- Provide the balanced equation in scene 4 (formula) using LaTeX.
"""
    elif subj == "physics":
        user_msg += """
PHYSICS-SPECIFIC:
- Must include scene_type "formula" with actual LaTeX formula.
- Must include scene_type "diagram" with appropriate diagram_type.
- Include a real numerical "example" scene with actual given values and step-by-step calculation.
"""
    elif subj == "mathematics":
        user_msg += """
MATHEMATICS-SPECIFIC:
- Must include scene_type "formula" with actual LaTeX expression.
- Include scene_type "diagram" if topic involves geometry or graphs.
- Include scene_type "example" with real numerical steps showing actual calculation.
"""

    user_msg += "\n6. Generate exactly 6 scenes following the subject-specific flow.\n"

    try:
        raw = await asyncio.to_thread(
            generate_json,
            prompt + "\n\n" + user_msg,
            temperature=0.2,
            max_output_tokens=4000,
        )

        parsed = json.loads(raw)
        validated = _validate_script(parsed, clean_title, subject)
        LOGGER.info("[script_generator] Generated %d scenes for '%s' (%s)",
                    len(validated["scenes"]), clean_title[:40], subject)
        return validated

    except (OpenAIClientError, json.JSONDecodeError, ValueError) as exc:
        if _fallback_enabled():
            LOGGER.warning("[script_generator] %s. Using local fallback script.", exc)
            return _build_local_script(clean_title, context, subject, class_level)
        raise