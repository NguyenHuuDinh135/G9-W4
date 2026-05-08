"""Generate W4 Presentation PPTX for Group 9 — GeekBrain AI Assistant.
Styled to match the HTML presentation with branded colors, cards, and layout.
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

BRAND_NAVY = RGBColor(0x1E, 0x29, 0x3B)
BRAND_ORANGE = RGBColor(0xFE, 0x76, 0x24)
BRAND_AMBER = RGBColor(0xFB, 0xAE, 0x42)
BRAND_BLUE = RGBColor(0x00, 0x7B, 0xC1)
BRAND_CYAN = RGBColor(0x00, 0xB3, 0xD9)
BRAND_GREEN = RGBColor(0x00, 0xAC, 0x4E)
BRAND_PURPLE = RGBColor(0x85, 0x43, 0x9A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xC4, 0xD5, 0xDD)
GRAY = RGBColor(0x4D, 0x4E, 0x4E)
MUTED = RGBColor(0x69, 0x86, 0x95)
SURFACE = RGBColor(0xF9, 0xFA, 0xFB)
RED = RGBColor(0xDC, 0x26, 0x26)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "..", "docs")
DIAGRAMS_DIR = os.path.join(DOCS_DIR, "diagrams")
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, "screenshots")

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)
FONT = "Plus Jakarta Sans"
FONT_MONO = "JetBrains Mono"


def set_slide_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_rounded_rect(slide, left, top, width, height, fill_color, border_color=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    shape.adjustments[0] = 0.05
    return shape


def add_text(slide, left, top, width, height, text, font_size=18, bold=False, color=BRAND_NAVY,
             align=PP_ALIGN.LEFT, v_align=MSO_ANCHOR.TOP, font_name=FONT, line_spacing=1.2):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = v_align
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = font_name
    p.alignment = align
    p.line_spacing = Pt(int(font_size * line_spacing))
    return txBox


def add_multiline(slide, left, top, width, height, lines, font_size=14, color=GRAY, font_name=FONT):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = font_name
        p.space_before = Pt(4)
    return txBox


def add_image_safe(slide, img_path, left, top, width=None, height=None):
    if not os.path.exists(img_path):
        return None
    kwargs = {"left": left, "top": top}
    if width:
        kwargs["width"] = width
    if height:
        kwargs["height"] = height
    return slide.shapes.add_picture(img_path, **kwargs)


def add_card(slide, left, top, width, height, title, body, accent_color=None, dark=False):
    bg_color = BRAND_NAVY if dark else SURFACE
    border = accent_color if accent_color else LIGHT_GRAY
    add_rounded_rect(slide, left, top, width, height, bg_color, border)

    if accent_color:
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Pt(5))
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent_color
        bar.line.fill.background()

    title_color = WHITE if dark else BRAND_NAVY
    body_color = LIGHT_GRAY if dark else GRAY

    add_text(slide, left + Inches(0.2), top + Inches(0.25), width - Inches(0.4), Inches(0.4),
             title, font_size=12, bold=True, color=title_color)
    add_text(slide, left + Inches(0.2), top + Inches(0.65), width - Inches(0.4), height - Inches(0.8),
             body, font_size=10, color=body_color, line_spacing=1.5)


def slide_title(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BRAND_NAVY)

    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(8), Inches(-1), Inches(7), Inches(7))
    circle.fill.solid()
    circle.fill.fore_color.rgb = RGBColor(0x2D, 0x3A, 0x55)
    circle.line.fill.background()

    circle2 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(-2), Inches(4), Inches(6), Inches(6))
    circle2.fill.solid()
    circle2.fill.fore_color.rgb = RGBColor(0x25, 0x32, 0x4A)
    circle2.line.fill.background()

    add_text(slide, Inches(1), Inches(1.2), Inches(4), Inches(0.3),
             "WEEK 4  •  GROUP 9", font_size=11, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(1), Inches(1.8), Inches(8), Inches(1.5),
             "GeekBrain\nAI Assistant.", font_size=48, bold=True, color=WHITE, line_spacing=1.0)
    add_text(slide, Inches(1), Inches(3.8), Inches(8), Inches(0.6),
             "RAG + Tool Calling + Memory", font_size=22, color=BRAND_ORANGE)

    add_multiline(slide, Inches(1), Inches(4.7), Inches(10), Inches(2.5), [
        "Le Hoang Trung Kien  •  Tran Dinh Bao Long  •  Nguyen Duc Chinh  •  Nguyen Huu Dinh",
        "Truong Thi My Quyen  •  Tran Van Duc  •  Hoang Trong Tan  •  Le Duy Khanh",
        "",
        "Mentor: Anh Quang Phung (QA Lead, TechX)",
        "LLM: DeepSeek V3.2 via Amazon Bedrock  •  Framework: Bedrock Agents",
    ], font_size=13, color=LIGHT_GRAY)


def slide_agenda(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text(slide, Inches(0.8), Inches(0.5), Inches(4), Inches(0.3),
             "AGENDA", font_size=10, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(0.8), Inches(0.9), Inches(8), Inches(0.7),
             "What we'll cover.", font_size=32, bold=True, color=BRAND_NAVY)

    cards = [
        ("01  Architecture", "System diagram, key decisions,\ndata flow through the pipeline.", BRAND_ORANGE),
        ("02  Individual Q&A", "Random members explain how\nthe system works internally.", BRAND_BLUE),
        ("03  Live Demo", "L1 → L2 → L3 → L4\nprogressive demonstration.", BRAND_GREEN),
        ("04  Lessons Learned", "Hardest level and what\nwe would change.", BRAND_PURPLE),
    ]

    x = Inches(0.8)
    for title, body, color in cards:
        add_card(slide, x, Inches(2.0), Inches(2.9), Inches(2.0), title, body, accent_color=color)
        x += Inches(3.1)


def slide_divider(prs, part_num, title, subtitle):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BRAND_NAVY)

    add_text(slide, Inches(0.8), Inches(1.0), Inches(5), Inches(3),
             f"{part_num:02d}", font_size=120, bold=True, color=RGBColor(0x2D, 0x3A, 0x55))
    add_text(slide, Inches(0.8), Inches(1.0), Inches(4), Inches(0.3),
             f"PART {part_num:02d}", font_size=10, bold=True, color=BRAND_AMBER)
    add_text(slide, Inches(0.8), Inches(3.5), Inches(10), Inches(1.2),
             title, font_size=40, bold=True, color=WHITE)
    add_text(slide, Inches(0.8), Inches(5.0), Inches(8), Inches(0.8),
             subtitle, font_size=16, color=LIGHT_GRAY)


def slide_architecture(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, Inches(0.8), Inches(0.4), Inches(4), Inches(0.3),
             "01 • ARCHITECTURE", font_size=10, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(0.8), Inches(0.8), Inches(8), Inches(0.6),
             "System Architecture.", font_size=28, bold=True, color=BRAND_NAVY)
    add_image_safe(slide, os.path.join(DIAGRAMS_DIR, "w4_architecture.png"),
                   Inches(0.3), Inches(1.6), width=Inches(12.7))


def slide_decisions(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, Inches(0.8), Inches(0.4), Inches(4), Inches(0.3),
             "01 • DECISIONS", font_size=10, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(0.8), Inches(0.8), Inches(8), Inches(0.6),
             "Key Technical Decisions.", font_size=28, bold=True, color=BRAND_NAVY)

    cards = [
        ("Bedrock Agents vs Custom Pipeline",
         "Managed orchestration. Agent handles\nKB retrieval + tool routing automatically.\nLess control, faster to production.", BRAND_GREEN),
        ("VPC Interface Endpoint (No NAT)",
         "VPC Endpoint for execute-api.\nTraffic stays on AWS backbone.\nNo NAT Gateway needed — saves cost.", BRAND_BLUE),
        ("Lambda Chat Outside VPC",
         "No vpc_config — calls Bedrock via\nAWS internal network. Avoids cold\nstart ENI delays (5-10s).", BRAND_CYAN),
        ("What Didn't Work",
         "DeepSeek V3.2 via Terraform\nfoundation_model param failed.\nFix: lifecycle { ignore_changes }\n+ manual console config.", RED),
    ]

    positions = [
        (Inches(0.8), Inches(1.7)), (Inches(6.8), Inches(1.7)),
        (Inches(0.8), Inches(4.2)), (Inches(6.8), Inches(4.2)),
    ]

    for (title, body, color), (x, y) in zip(cards, positions):
        add_card(slide, x, y, Inches(5.7), Inches(2.2), title, body, accent_color=color)


def slide_request_flow(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, Inches(0.8), Inches(0.4), Inches(4), Inches(0.3),
             "01 • DATA FLOW", font_size=10, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(0.8), Inches(0.8), Inches(10), Inches(0.6),
             "Request Flow & Orchestration Loop.", font_size=28, bold=True, color=BRAND_NAVY)
    add_image_safe(slide, os.path.join(DIAGRAMS_DIR, "w4_request_flow.png"),
                   Inches(0.3), Inches(1.6), width=Inches(12.7))


def slide_tool_routing(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, Inches(0.8), Inches(0.4), Inches(4), Inches(0.3),
             "01 • TOOL ROUTING", font_size=10, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(0.8), Inches(0.8), Inches(10), Inches(0.6),
             "Agent Decision Logic — KB vs Tools.", font_size=28, bold=True, color=BRAND_NAVY)
    add_image_safe(slide, os.path.join(DIAGRAMS_DIR, "w4_tool_routing.png"),
                   Inches(0.3), Inches(1.6), width=Inches(12.7))


def slide_level(prs, level_num, level_title, description, screenshot, proof=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    color_map = {1: BRAND_GREEN, 2: BRAND_BLUE, 3: BRAND_ORANGE, 4: BRAND_PURPLE}
    accent = color_map.get(level_num, BRAND_ORANGE)
    label_map = {1: "RAG", 2: "MULTI-SOURCE", 3: "TOOLS", 4: "MEMORY"}

    add_text(slide, Inches(0.8), Inches(0.4), Inches(5), Inches(0.3),
             f"L{level_num} • {label_map[level_num]}", font_size=10, bold=True, color=accent)
    add_text(slide, Inches(0.8), Inches(0.8), Inches(10), Inches(0.5),
             f"L{level_num} — {level_title}.", font_size=26, bold=True, color=BRAND_NAVY)
    add_text(slide, Inches(0.8), Inches(1.35), Inches(11), Inches(0.5),
             description, font_size=12, color=GRAY)

    img_path = os.path.join(SCREENSHOTS_DIR, screenshot)
    if proof:
        proof_path = os.path.join(SCREENSHOTS_DIR, proof)
        add_image_safe(slide, img_path, Inches(0.4), Inches(2.0), width=Inches(6.2))
        add_image_safe(slide, proof_path, Inches(6.8), Inches(2.0), width=Inches(6.2))
    else:
        add_image_safe(slide, img_path, Inches(1.5), Inches(2.0), width=Inches(10.3))


def slide_bonus_a(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, Inches(0.8), Inches(0.4), Inches(5), Inches(0.3),
             "BONUS A • OBSERVABILITY", font_size=10, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(0.8), Inches(0.8), Inches(10), Inches(0.5),
             "Observability Dashboard (+0.5)", font_size=26, bold=True, color=BRAND_NAVY)
    add_text(slide, Inches(0.8), Inches(1.35), Inches(11), Inches(0.4),
             "Pipeline internals: source tags (green), tool badges (purple), query details, full orchestration trace.",
             font_size=12, color=GRAY)
    add_image_safe(slide, os.path.join(SCREENSHOTS_DIR, "bonus_a.png"),
                   Inches(1.2), Inches(2.0), width=Inches(10.8))


def slide_bonus_c(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, Inches(0.8), Inches(0.4), Inches(5), Inches(0.3),
             "BONUS C • KB SYNC", font_size=10, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(0.8), Inches(0.8), Inches(10), Inches(0.5),
             "Knowledge Base Auto-Sync (+0.5)", font_size=26, bold=True, color=BRAND_NAVY)

    steps = [
        ("01  Detect Change", "MD5 hash trigger detects\n.md file updates in S3.", BRAND_ORANGE),
        ("02  Start Ingestion", "null_resource.kb_sync runs\naws bedrock-agent\nstart-ingestion-job", BRAND_BLUE),
        ("03  Poll Complete", "Polls until COMPLETE.\nTimeout: 10 min.\nFully automated via Terraform.", BRAND_GREEN),
    ]

    x = Inches(0.8)
    for title, body, color in steps:
        add_card(slide, x, Inches(1.8), Inches(3.7), Inches(2.2), title, body, accent_color=color)
        x += Inches(4.0)

    add_text(slide, Inches(0.8), Inches(4.5), Inches(11), Inches(0.4),
             "Evidence: terraform/modules/ai_engine/main.tf — kb_sync resource",
             font_size=11, color=MUTED, font_name=FONT_MONO)


def slide_lessons(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, Inches(0.8), Inches(0.4), Inches(5), Inches(0.3),
             "04 • REFLECTION", font_size=10, bold=True, color=BRAND_ORANGE)
    add_text(slide, Inches(0.8), Inches(0.8), Inches(8), Inches(0.6),
             "Lessons Learned.", font_size=28, bold=True, color=BRAND_NAVY)

    add_card(slide, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0),
             "Hardest Level: L3",
             'Tool descriptions must be\nextremely precise.\n\n'
             '"Gets data" → useless.\n'
             '"Returns CURRENT live metrics;\nfor HISTORICAL data use\nquery_database" → works.\n\n'
             'Iterated multiple times before\nagent routed correctly.',
             dark=True)

    add_card(slide, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0),
             "What we'd do differently",
             '• Add query rewriting for L4\n'
             '  (pronouns → explicit references)\n\n'
             '• Automated testing with\n'
             '  question JSON files\n\n'
             '• Fallback error messages when\n'
             '  Monitoring API is unreachable',
             accent_color=BRAND_ORANGE)


def slide_thankyou(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BRAND_NAVY)

    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(9), Inches(4), Inches(6), Inches(6))
    circle.fill.solid()
    circle.fill.fore_color.rgb = RGBColor(0x2D, 0x3A, 0x55)
    circle.line.fill.background()

    add_text(slide, Inches(0.8), Inches(2.0), Inches(11.5), Inches(1.2),
             "Thank You!", font_size=52, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_text(slide, Inches(0.8), Inches(3.5), Inches(11.5), Inches(0.6),
             "Group 9 — GeekBrain AI Assistant", font_size=22, color=BRAND_ORANGE, align=PP_ALIGN.CENTER)
    add_multiline(slide, Inches(2), Inches(4.5), Inches(9), Inches(1.5), [
        "Evidence Pack: docs/W4_evidence.md",
        "Repo: github.com/hoang-trong-tan/G9-W4",
        "", "Questions?",
    ], font_size=14, color=LIGHT_GRAY)


def main():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    slide_title(prs)
    slide_agenda(prs)
    slide_divider(prs, 1, "System Architecture.",
                  "How requests flow through Bedrock Agent, Knowledge Base, and Tools\n— all on AWS with no NAT Gateway.")
    slide_architecture(prs)
    slide_decisions(prs)
    slide_request_flow(prs)
    slide_tool_routing(prs)
    slide_divider(prs, 3, "Live Demo.",
                  "L1 → L2 → L3 → L4 — progressive levels of AI capability.")
    slide_level(prs, 1, "Simple RAG (Retrieval)",
                "36 markdown docs → Titan Embed v2 (1024d) → OpenSearch Serverless → top-K chunks → answer + source citation",
                "l1_answer.png", "l1_proof.png")
    slide_level(prs, 2, "Multi-Source Retrieval",
                "Multi-doc synthesis & conflict resolution. Agent prefers most recent version (status='current' over 'archived')",
                "l2_answer.png", "l2_proof.png")
    slide_level(prs, 3, "Tool-Augmented RAG",
                "6 tools: query_database, get_service_metrics, get_service_status, list_services, get_incident_history, compare_services",
                "l3_answer.png", "l3_proof.png")
    slide_level(prs, 4, "Memory (Multi-turn)",
                'Bedrock Agent sessionId (TTL: 1800s). Pronouns like "its costs" and "that service" resolved across turns.',
                "l4_conversation.png")
    slide_bonus_a(prs)
    slide_bonus_c(prs)
    slide_lessons(prs)
    slide_thankyou(prs)

    output_path = os.path.join(BASE_DIR, "W4_presentation.pptx")
    prs.save(output_path)
    print(f"Saved: {output_path}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    main()
