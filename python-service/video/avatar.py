from manim import *

def create_avatar():
    """
    Creates a simple geometric teacher avatar using Manim shapes.
    Returns a VGroup that can be added to any scene.
    Positioned in bottom-left corner.
    """
    # Head
    head = Circle(radius=0.28, color=YELLOW, fill_opacity=1, stroke_color=ORANGE)
    
    # Eyes (two small dots)
    left_eye = Dot(radius=0.05, color=BLACK).move_to(head.get_center() + LEFT * 0.1 + UP * 0.08)
    right_eye = Dot(radius=0.05, color=BLACK).move_to(head.get_center() + RIGHT * 0.1 + UP * 0.08)
    
    # Smile
    smile = Arc(radius=0.12, angle=-PI/2, color=BLACK, stroke_width=2)
    smile.move_to(head.get_center() + DOWN * 0.08)
    
    # Body (rectangle)
    body = Rectangle(width=0.5, height=0.55, color=BLUE, fill_opacity=1, stroke_color=BLUE_D)
    body.next_to(head, DOWN, buff=0.05)
    
    # Collar/tie indicator
    tie = Triangle(color=RED, fill_opacity=1).scale(0.1)
    tie.move_to(body.get_top() + DOWN * 0.1)
    
    # Arms
    left_arm = Line(
        body.get_left() + UP * 0.1,
        body.get_left() + LEFT * 0.3 + DOWN * 0.2,
        color=YELLOW, stroke_width=4
    )
    right_arm = Line(
        body.get_right() + UP * 0.1,
        body.get_right() + RIGHT * 0.3 + DOWN * 0.2,
        color=YELLOW, stroke_width=4
    )
    
    # Legs
    left_leg = Line(body.get_bottom() + LEFT * 0.1, body.get_bottom() + LEFT * 0.15 + DOWN * 0.4, color=BLUE_D, stroke_width=4)
    right_leg = Line(body.get_bottom() + RIGHT * 0.1, body.get_bottom() + RIGHT * 0.15 + DOWN * 0.4, color=BLUE_D, stroke_width=4)

    avatar = VGroup(head, left_eye, right_eye, smile, body, tie, left_arm, right_arm, left_leg, right_leg)
    
    # Scale and position in bottom-left corner
    avatar.scale(0.85)
    avatar.move_to([-5.5, -3.0, 0])
    
    return avatar


def create_talking_animation(avatar, duration):
    """
    Creates a subtle talking animation — slight bob up/down on the head.
    Returns list of animations to play.
    """
    head = avatar[0]  # head is first element
    
    animations = []
    num_bobs = int(duration / 0.4)  # one bob every 0.4 seconds
    
    for i in range(num_bobs):
        if i % 2 == 0:
            animations.append(head.animate.shift(UP * 0.04))
        else:
            animations.append(head.animate.shift(DOWN * 0.04))
    
    return animations


def add_speech_bubble(avatar, text_content):
    """
    Small speech bubble next to avatar showing key word being said.
    """
    bubble_text = Text(text_content[:20], font_size=16, color=BLACK)
    bubble_bg = RoundedRectangle(
        width=bubble_text.width + 0.3,
        height=0.4,
        corner_radius=0.1,
        color=WHITE,
        fill_opacity=1,
        stroke_color=GRAY
    )
    bubble_bg.move_to(avatar.get_right() + RIGHT * (bubble_bg.width / 2 + 0.1) + UP * 0.3)
    bubble_text.move_to(bubble_bg.get_center())
    
    return VGroup(bubble_bg, bubble_text)