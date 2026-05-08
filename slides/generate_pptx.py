"""Generate W4 Presentation PPTX for Group 9 — GeekBrain AI Assistant."""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

BRAND_NAVY = RGBColor(0x1E, 0x29, 0x3B)
BRAND_ORANGE = RGBColor(0xFE, 0x76, 0x24)
BRAND_BLUE = RGBColor(0x00, 0x7B, 0xC1)
BRAND_GREEN = RGBColor(0x00, 0xAC, 0x4E)
BRAND_PURPLE = RGBColor(0x85, 0x43, 0x9A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x4D, 0x4E, 0x4E)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "..", "docs")
DIAGRAMS_DIR = os.path.join(DOCS_DIR, "diagrams")
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, "screenshots")

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


def set_slide_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_text_box(slide, left, top, width, height, text, font_size=18,
                 bold=False, color=BRAND_NAVY, align=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.font.name = "Calibri"
    p.alignment = align
    return txBox


def add_bullet_list(slide, left, top, width, height, items, font_size=16, color=GRAY):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = "Calibri"
        p.space_before = Pt(6)
        p.level = 0
    return txBox


def add_image_safe(slide, img_path, left, top, width=None, height=None):
    if os.path.exists(img_path):
        if width and height:
            slide.shapes.add_picture(img_path, left, top, width, height)
        elif width:
            slide.shapes.add_picture(img_path, left, top, width=width)
        elif height:
            slide.shapes.add_picture(img_path, left, top, height=height)
        else:
            slide.shapes.add_picture(img_path, left, top)
        return True
    return False


def make_title_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BRAND_NAVY)

    add_text_box(slide, Inches(0.8), Inches(1.5), Inches(11), Inches(1.2),
                 "GeekBrain AI Assistant", font_size=44, bold=True, color=WHITE)

    add_text_box(slide, Inches(0.8), Inches(2.7), Inches(11), Inches(0.8),
                 "Week 4 — RAG + Tools + Memory", font_size=28, color=BRAND_ORANGE)

    info_lines = [
        "Group 9",
        "",
        "Le Hoang Trung Kien  •  Tran Dinh Bao Long  •  Nguyen Duc Chinh",
        "Nguyen Huu Dinh  •  Truong Thi My Quyen  •  Tran Van Duc  •  Hoang Trong Tan",
        "",
        "Mentor: Anh Quang Phung (Quality Assurance Lead, TechX)",
        "LLM: DeepSeek V3.2 via Amazon Bedrock",
        "Framework: Amazon Bedrock Agents (managed orchestration)",
    ]
    add_bullet_list(slide, Inches(0.8), Inches(3.8), Inches(11), Inches(3.5),
                    info_lines, font_size=16, color=RGBColor(0xC4, 0xD5, 0xDD))


def make_agenda_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text_box(slide, Inches(0.8), Inches(0.5), Inches(5), Inches(0.5),
                 "AGENDA", font_size=14, bold=True, color=BRAND_ORANGE)
    add_text_box(slide, Inches(0.8), Inches(1.0), Inches(10), Inches(0.8),
                 "What we'll cover today.", font_size=36, bold=True, color=BRAND_NAVY)

    items = [
        "1.  Architecture Overview  (3 min)",
        "     System diagram  •  Key decisions  •  Data flow",
        "",
        "2.  Individual Q&A  (3 min)",
        "     Random members explain system internals",
        "",
        "3.  Live Demo  (4-5 min)",
        "     L1 → L2 → L3 → L4 progressive demonstration",
        "",
        "4.  Lessons Learned  (1 min)",
        "     Hardest level  •  What we'd change",
    ]
    add_bullet_list(slide, Inches(1.2), Inches(2.2), Inches(10), Inches(5),
                    items, font_size=18, color=GRAY)


def make_architecture_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text_box(slide, Inches(0.8), Inches(0.3), Inches(5), Inches(0.4),
                 "01 • ARCHITECTURE", font_size=12, bold=True, color=BRAND_ORANGE)
    add_text_box(slide, Inches(0.8), Inches(0.7), Inches(10), Inches(0.6),
                 "System Architecture", font_size=30, bold=True, color=BRAND_NAVY)

    img = os.path.join(DIAGRAMS_DIR, "w4_architecture.png")
    add_image_safe(slide, img, Inches(0.5), Inches(1.5), width=Inches(12.3))


def make_decisions_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text_box(slide, Inches(0.8), Inches(0.3), Inches(5), Inches(0.4),
                 "01 • DECISIONS", font_size=12, bold=True, color=BRAND_ORANGE)
    add_text_box(slide, Inches(0.8), Inches(0.7), Inches(10), Inches(0.6),
                 "Key Technical Decisions", font_size=30, bold=True, color=BRAND_NAVY)

    decisions = [
        ("Bedrock Agents vs Custom Pipeline",
         "Chose managed orchestration — Agent handles KB retrieval + tool routing automatically. Trade-off: less control, faster to production."),
        ("VPC Interface Endpoint vs NAT Gateway",
         "Chose VPC Endpoint for API Gateway. Keeps traffic on AWS backbone, saves ~$32/month NAT cost, reduces latency."),
        ("Lambda Chat Outside VPC",
         "No vpc_config — calls Bedrock directly via AWS internal network. Avoids cold start ENI delays (5-10s)."),
        ("What Didn't Work",
         "DeepSeek V3.2 via Terraform foundation_model failed. Fix: lifecycle ignore_changes + manual console config."),
    ]

    y = Inches(1.6)
    for title, desc in decisions:
        add_text_box(slide, Inches(1.0), y, Inches(11), Inches(0.4),
                     f"▸ {title}", font_size=16, bold=True, color=BRAND_NAVY)
        y += Inches(0.45)
        add_text_box(slide, Inches(1.3), y, Inches(10.5), Inches(0.7),
                     desc, font_size=14, color=GRAY)
        y += Inches(0.75)


def make_request_flow_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text_box(slide, Inches(0.8), Inches(0.3), Inches(5), Inches(0.4),
                 "01 • DATA FLOW", font_size=12, bold=True, color=BRAND_ORANGE)
    add_text_box(slide, Inches(0.8), Inches(0.7), Inches(10), Inches(0.6),
                 "Request Flow & Orchestration Loop", font_size=30, bold=True, color=BRAND_NAVY)

    img = os.path.join(DIAGRAMS_DIR, "w4_request_flow.png")
    add_image_safe(slide, img, Inches(0.5), Inches(1.5), width=Inches(12.3))


def make_tool_routing_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text_box(slide, Inches(0.8), Inches(0.3), Inches(5), Inches(0.4),
                 "01 • TOOL ROUTING", font_size=12, bold=True, color=BRAND_ORANGE)
    add_text_box(slide, Inches(0.8), Inches(0.7), Inches(10), Inches(0.6),
                 "Agent Decision Logic — KB vs Tools", font_size=30, bold=True, color=BRAND_NAVY)

    img = os.path.join(DIAGRAMS_DIR, "w4_tool_routing.png")
    add_image_safe(slide, img, Inches(0.5), Inches(1.5), width=Inches(12.3))


def make_level_slide(prs, level_num, level_title, description, screenshot_file, proof_file=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    color_map = {"1": BRAND_GREEN, "2": BRAND_BLUE, "3": BRAND_ORANGE, "4": BRAND_PURPLE}
    accent = color_map.get(str(level_num), BRAND_ORANGE)

    add_text_box(slide, Inches(0.8), Inches(0.3), Inches(5), Inches(0.4),
                 f"03 • DEMO L{level_num}", font_size=12, bold=True, color=accent)
    add_text_box(slide, Inches(0.8), Inches(0.7), Inches(10), Inches(0.6),
                 f"L{level_num} — {level_title}", font_size=30, bold=True, color=BRAND_NAVY)
    add_text_box(slide, Inches(0.8), Inches(1.3), Inches(10), Inches(0.5),
                 description, font_size=14, color=GRAY)

    img = os.path.join(SCREENSHOTS_DIR, screenshot_file)
    if proof_file:
        add_image_safe(slide, img, Inches(0.5), Inches(2.0), width=Inches(6.0))
        proof_img = os.path.join(SCREENSHOTS_DIR, proof_file)
        add_image_safe(slide, proof_img, Inches(6.8), Inches(2.0), width=Inches(6.0))
    else:
        add_image_safe(slide, img, Inches(1.5), Inches(2.0), width=Inches(10.0))


def make_bonus_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text_box(slide, Inches(0.8), Inches(0.3), Inches(5), Inches(0.4),
                 "03 • BONUS", font_size=12, bold=True, color=BRAND_ORANGE)
    add_text_box(slide, Inches(0.8), Inches(0.7), Inches(10), Inches(0.6),
                 "Bonus A — Observability Dashboard (+0.5)", font_size=28, bold=True, color=BRAND_NAVY)

    add_text_box(slide, Inches(0.8), Inches(1.3), Inches(10), Inches(0.5),
                 "Frontend displays pipeline internals: source tags (green), tool badges (purple), query details, full trace",
                 font_size=14, color=GRAY)

    img = os.path.join(SCREENSHOTS_DIR, "bonus_a.png")
    add_image_safe(slide, img, Inches(1.5), Inches(2.0), width=Inches(10.0))


def make_bonus_c_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text_box(slide, Inches(0.8), Inches(0.3), Inches(5), Inches(0.4),
                 "03 • BONUS", font_size=12, bold=True, color=BRAND_ORANGE)
    add_text_box(slide, Inches(0.8), Inches(0.7), Inches(10), Inches(0.6),
                 "Bonus C — Knowledge Base Sync (+0.5)", font_size=28, bold=True, color=BRAND_NAVY)

    items = [
        "Automated via Terraform — no manual intervention needed",
        "",
        "How it works:",
        "  1. Upload .md files to S3 (MD5 hash change detected)",
        "  2. null_resource.kb_sync triggers aws bedrock-agent start-ingestion-job",
        "  3. Polls until COMPLETE (timeout: 10 min)",
        "",
        "Result: Knowledge Base stays in sync with latest documents",
        "",
        "Evidence: terraform/modules/ai_engine/main.tf — kb_sync resource",
    ]
    add_bullet_list(slide, Inches(1.2), Inches(1.8), Inches(10), Inches(5),
                    items, font_size=18, color=GRAY)


def make_lessons_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    add_text_box(slide, Inches(0.8), Inches(0.3), Inches(5), Inches(0.4),
                 "04 • REFLECTION", font_size=12, bold=True, color=BRAND_ORANGE)
    add_text_box(slide, Inches(0.8), Inches(0.7), Inches(10), Inches(0.6),
                 "Lessons Learned", font_size=30, bold=True, color=BRAND_NAVY)

    items = [
        "Hardest Level: L3 — Tool-Augmented RAG",
        "",
        "Why:",
        '  • Tool descriptions must be extremely precise',
        '  • "Gets data" is useless — "Returns CURRENT live metrics;',
        '    for HISTORICAL data use query_database" made the difference',
        "  • Iterated descriptions multiple times before agent routed correctly",
        "",
        "What we'd do differently with one more day:",
        "  • Add query rewriting for L4 (pronouns → explicit references)",
        "  • Implement automated testing with question JSON files",
        "  • Add fallback error messages when Monitoring API is unreachable",
    ]
    add_bullet_list(slide, Inches(1.0), Inches(1.6), Inches(11), Inches(5.5),
                    items, font_size=17, color=GRAY)


def make_thankyou_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BRAND_NAVY)

    add_text_box(slide, Inches(0.8), Inches(2.5), Inches(11), Inches(1.0),
                 "Thank You!", font_size=48, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(0.8), Inches(3.8), Inches(11), Inches(0.6),
                 "Group 9 — GeekBrain AI Assistant", font_size=22, color=BRAND_ORANGE, align=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(0.8), Inches(4.8), Inches(11), Inches(1.0),
                 "Evidence Pack: docs/W4_evidence.md\nRepo: github.com/hoang-trong-tan/G9-W4",
                 font_size=16, color=RGBColor(0xC4, 0xD5, 0xDD), align=PP_ALIGN.CENTER)


def main():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    make_title_slide(prs)
    make_agenda_slide(prs)
    make_architecture_slide(prs)
    make_decisions_slide(prs)
    make_request_flow_slide(prs)
    make_tool_routing_slide(prs)

    make_level_slide(prs, 1, "Simple RAG (Retrieval)",
                     "Single-doc retrieval with source citation. KB: 36 markdown docs → Titan Embed v2 → OpenSearch Serverless",
                     "l1_answer.png", "l1_proof.png")
    make_level_slide(prs, 2, "Multi-Source Retrieval",
                     "Multi-doc synthesis & conflict resolution. Agent prefers most recent version (status='current' over 'archived')",
                     "l2_answer.png", "l2_proof.png")
    make_level_slide(prs, 3, "Tool-Augmented RAG",
                     "6 tools: query_database, get_service_metrics, get_service_status, list_services, get_incident_history, compare_services",
                     "l3_answer.png", "l3_proof.png")
    make_level_slide(prs, 4, "Memory (Multi-turn Conversation)",
                     "Bedrock Agent sessionId (TTL: 1800s). Pronouns resolved across turns without user repeating context.",
                     "l4_conversation.png")

    make_bonus_slide(prs)
    make_bonus_c_slide(prs)
    make_lessons_slide(prs)
    make_thankyou_slide(prs)

    output_path = os.path.join(BASE_DIR, "W4_presentation.pptx")
    prs.save(output_path)
    print(f"Saved: {output_path}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    main()
