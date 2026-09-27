"""Design guidance and technique references fed to HTMLAgent's prompt.

These exist to push slide output away from generic "AI-slop" patterns
(uppercase eyebrow labels, identical rounded cards with matching shadows,
em-dash labels, etc.) toward compositions that are deliberate and grounded
in the slide's actual content. The example snippets are technique
references, not templates to copy verbatim — the prompt says so explicitly,
and different slides in a deck are shown different examples so a whole
deck doesn't converge on one look.
"""

DESIGN_PRINCIPLES = """
Design like a studio that gives every client a distinct visual identity —
not a generic template. Make deliberate choices grounded in THIS slide's
actual content, not reflexive defaults.

- Spend boldness in one place: pick ONE dominant visual move for this
  slide (a huge number, a striking quote, a strong asymmetric split) and
  keep everything else quiet and disciplined around it.
- Vary alignment and composition — not everything centered, not everything
  the same split ratio. An off-center or asymmetric layout (e.g. 35/65,
  not 50/50) usually reads as more considered than a symmetric one.
- Use the theme's accent color sparingly, on the one focal element — not
  scattered as borders/highlights on every element.
- Write specific, concrete text grounded in this slide's real content.
  Never generic placeholder-sounding lines.
"""

AVOID_LIST = """
Do NOT use these — they are the most common tells of generic AI-generated
slides:
- An uppercase, letter-spaced "eyebrow" label above a headline (e.g.
  "INVESTOR BRIEFING", "OUR APPROACH").
- Multiple identical rounded-corner cards with the same soft grey
  box-shadow — the generic "SaaS card grid". If you use cards, make at
  most one visually dominant; keep the rest flatter and quieter.
- Numbered markers (01 / 02 / 03) unless the content is a genuine
  sequence (a timeline or process) — most slides are not.
- Middle-dot separators ("A · B · C"), em-dash labels ("Word — fragment"),
  monospace font for small data labels, or a trailing arrow (→) on text.
- The reflexive palette defaults: warm cream background with a serif
  headline and a terracotta/clay accent, OR near-black background with a
  single neon-green/vermilion accent. Use the theme's actual given colors
  instead, applied deliberately.
"""

EXAMPLES = [
    {
        "name": "bold_focal_stat",
        "best_for": ("hero", "data_story"),
        "html": """<div style="width:100%;height:100%;background:#0b1220;color:#f1f5f9;display:flex;align-items:flex-end;padding:6% 7%;font-family:Georgia,serif;position:relative;overflow:hidden;">
  <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 15% 20%, rgba(37,99,235,0.18), transparent 55%);"></div>
  <div style="position:relative;display:flex;align-items:flex-end;gap:5%;width:100%;">
    <div style="font-size:clamp(90px,13vw,190px);line-height:0.85;font-weight:700;color:#2563eb;flex:0 0 auto;">73%</div>
    <div style="max-width:420px;padding-bottom:1.2%;">
      <p style="font-size:22px;line-height:1.35;margin:0 0 10px 0;">of emissions disappear when fossil fuels leave the grid.</p>
      <p style="font-size:15px;line-height:1.5;margin:0;color:#94a3b8;font-family:Inter,sans-serif;">Modeled across four national grids, 2019–2024.</p>
    </div>
  </div>
</div>""",
    },
    {
        "name": "sequential_ruleline",
        "best_for": ("timeline", "process"),
        "html": """<div style="width:100%;height:100%;background:#faf9f7;color:#1c1917;display:flex;flex-direction:column;justify-content:center;padding:6% 8%;font-family:Inter,sans-serif;">
  <h2 style="font-size:30px;font-weight:600;margin:0 0 40px 0;max-width:70%;">From pilot to national rollout in three phases</h2>
  <div style="display:flex;align-items:flex-start;position:relative;">
    <div style="position:absolute;top:9px;left:0;right:0;height:1px;background:#d6d3d1;"></div>
    <div style="flex:1;padding-right:24px;">
      <div style="width:9px;height:9px;border-radius:50%;background:#b45309;margin-bottom:16px;"></div>
      <p style="font-weight:600;margin:0 0 6px 0;">2024 — Field pilot</p>
      <p style="font-size:14px;color:#57534e;margin:0;line-height:1.5;">12 sites, manual monitoring</p>
    </div>
    <div style="flex:1;padding-right:24px;">
      <div style="width:9px;height:9px;border-radius:50%;background:#d6d3d1;margin-bottom:16px;"></div>
      <p style="font-weight:600;margin:0 0 6px 0;">2025 — Regional expansion</p>
      <p style="font-size:14px;color:#57534e;margin:0;line-height:1.5;">140 sites, automated sensors</p>
    </div>
    <div style="flex:1;">
      <div style="width:9px;height:9px;border-radius:50%;background:#d6d3d1;margin-bottom:16px;"></div>
      <p style="font-weight:600;margin:0 0 6px 0;">2026 — National rollout</p>
      <p style="font-size:14px;color:#57534e;margin:0;line-height:1.5;">Full grid coverage</p>
    </div>
  </div>
</div>""",
    },
    {
        "name": "editorial_asymmetric_split",
        "best_for": ("comparison", "split", "grid"),
        "html": """<div style="width:100%;height:100%;display:flex;font-family:Georgia,serif;background:#ffffff;">
  <div style="flex:0 0 34%;background:#1c1917;color:#fafaf9;padding:7% 6%;display:flex;flex-direction:column;justify-content:center;">
    <p style="font-size:28px;line-height:1.3;margin:0;font-style:italic;">"The grid we inherited wasn't built for this much solar."</p>
    <p style="font-size:14px;color:#a8a29e;margin-top:20px;font-family:Inter,sans-serif;">Head of Infrastructure, national utility</p>
  </div>
  <div style="flex:1;padding:7% 6%;display:flex;flex-direction:column;justify-content:center;">
    <h2 style="font-family:Inter,sans-serif;font-size:26px;font-weight:600;color:#1c1917;margin:0 0 18px 0;max-width:80%;">Storage is the bottleneck, not generation</h2>
    <p style="font-family:Inter,sans-serif;font-size:16px;line-height:1.6;color:#44403c;max-width:85%;margin:0;">Panel costs have fallen 82% in a decade. Battery capacity hasn't kept pace, and it's now the single largest constraint on new solar approvals.</p>
  </div>
</div>""",
    },
]


def pick_example(slide_type: str, index: int) -> dict:
    for example in EXAMPLES:
        if slide_type in example["best_for"]:
            return example
    return EXAMPLES[index % len(EXAMPLES)]
