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
- If the content describes a process, dependency, or sequence of steps,
  consider drawing an actual node-and-arrow diagram in inline <svg> —
  real boxes connected by arrows showing what leads to what — rather than
  a text list. This is far more convincing than prose for "X and Y both
  have to happen before Z."
- For a schedule/timeline with real durations, draw proportional bars
  (width reflecting duration) rather than evenly-spaced dots — and give an
  uncertain/estimated range a visibly different treatment (e.g. a dashed
  border or hatched fill) from a confirmed range (solid fill).
- If a slide's sidebar or supporting area has 2-3 small callouts, give each
  one a genuinely different treatment (e.g. one dark/filled "hero" card
  with a large number, one with just a colored left border, one plain) —
  never the same card style repeated.
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
        "name": "process_flow_diagram",
        "best_for": ("process", "data_story"),
        "html": """<div style="width:100%;height:100%;background:#ffffff;color:#0f1b33;font-family:Inter,sans-serif;padding:6% 7%;display:flex;flex-direction:column;">
  <h1 style="font-size:32px;font-weight:800;letter-spacing:-0.02em;line-height:1.15;margin:0 0 10px 0;max-width:26ch;">The referral link is easy. MaxifyIP needs to be sellable first.</h1>
  <p style="font-size:16px;color:#5b6680;line-height:1.5;max-width:60ch;margin:0 0 28px 0;">Zefyron sends users to MaxifyIP and earns a commission on purchase. Today there's nothing on MaxifyIP for a referral to attach to.</p>
  <div style="display:grid;grid-template-columns:340px 1fr;gap:48px;flex:1;">
    <div>
      <h2 style="font-size:13px;font-weight:700;color:#5b6680;margin:0 0 12px 0;">What's missing today</h2>
      <div style="display:flex;gap:14px;padding:14px 0;border-top:1px solid #dce2ec;">
        <div style="flex:none;width:24px;height:24px;border-radius:50%;background:#fbe7e3;color:#b8412f;font-weight:800;font-size:13px;display:flex;align-items:center;justify-content:center;">✕</div>
        <div><b style="display:block;font-size:16px;">No login</b><span style="font-size:14px;color:#5b6680;">No accounts, so a referred user can't be identified.</span></div>
      </div>
      <div style="display:flex;gap:14px;padding:14px 0;border-top:1px solid #dce2ec;border-bottom:1px solid #dce2ec;">
        <div style="flex:none;width:24px;height:24px;border-radius:50%;background:#fbe7e3;color:#b8412f;font-weight:800;font-size:13px;display:flex;align-items:center;justify-content:center;">✕</div>
        <div><b style="display:block;font-size:16px;">No payments</b><span style="font-size:14px;color:#5b6680;">No purchase event, so there's nothing to pay commission on.</span></div>
      </div>
    </div>
    <div style="background:#f3f6fa;border-radius:10px;padding:24px 28px;">
      <h2 style="font-size:13px;font-weight:700;color:#5b6680;margin:0 0 16px 0;">What has to happen, in order</h2>
      <svg viewBox="0 0 560 200" width="100%" height="160">
        <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6680"/></marker></defs>
        <path d="M180 50 C 220 50, 220 100, 260 100" stroke="#5b6680" stroke-width="2" fill="none" marker-end="url(#a)"/>
        <path d="M180 150 C 220 150, 220 100, 260 100" stroke="#5b6680" stroke-width="2" fill="none" marker-end="url(#a)"/>
        <rect x="0" y="16" width="170" height="64" rx="8" fill="none" stroke="#c9781a" stroke-width="2"/>
        <text x="14" y="42" font-size="14" font-weight="700" fill="#0f1b33">Map patent data</text>
        <text x="14" y="62" font-size="12" fill="#5b6680">to scoring format</text>
        <rect x="0" y="116" width="170" height="64" rx="8" fill="none" stroke="#c9781a" stroke-width="2"/>
        <text x="14" y="142" font-size="14" font-weight="700" fill="#0f1b33">Login + payments</text>
        <rect x="264" y="70" width="140" height="64" rx="8" fill="#c9781a"/>
        <text x="278" y="98" font-size="14" font-weight="700" fill="#fff">MaxifyIP is</text>
        <text x="278" y="118" font-size="14" font-weight="700" fill="#fff">sellable</text>
      </svg>
      <p style="font-size:13px;color:#0f1b33;border-left:3px solid #2b5bd7;padding-left:10px;margin-top:12px;">Referral tracking can't be built until there's an account to link and a purchase to track.</p>
    </div>
  </div>
</div>""",
    },
    {
        "name": "gantt_timeline",
        "best_for": ("timeline",),
        "html": """<div style="width:100%;height:100%;background:#ffffff;color:#0f1b33;font-family:Inter,sans-serif;padding:6% 7%;display:flex;flex-direction:column;">
  <h1 style="font-size:30px;font-weight:800;letter-spacing:-0.02em;margin:0 0 28px 0;">Realistic timeline: 3–5 weeks, in two phases</h1>
  <div style="display:grid;grid-template-columns:1fr 220px;gap:40px;flex:1;">
    <div>
      <div style="display:grid;grid-template-columns:190px 1fr;row-gap:14px;">
        <div></div>
        <div style="display:grid;grid-template-columns:repeat(5,1fr);font-size:12px;font-weight:600;color:#5b6680;border-bottom:1px solid #dce2ec;padding-bottom:8px;">
          <span>Week 1</span><span>Week 2</span><span>Week 3</span><span>Week 4</span><span>Week 5</span>
        </div>
        <div style="grid-column:1/-1;font-size:12px;font-weight:700;color:#5b6680;margin-top:6px;">Phase 1: foundations, run in parallel</div>
        <div style="font-size:15px;font-weight:700;">Data mapping</div>
        <div style="position:relative;height:32px;background:repeating-linear-gradient(to right,#dce2ec 0 1px,transparent 1px 20%);">
          <div style="position:absolute;left:0;width:20%;top:5px;height:22px;border-radius:4px;background:#c9781a;color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;padding-left:8px;">1 wk</div>
          <div style="position:absolute;left:20%;width:40%;top:5px;height:22px;border-radius:0 4px 4px 0;border:1.5px dashed #c9781a;color:#c9781a;font-size:12px;font-weight:700;display:flex;align-items:center;padding-left:8px;">up to 3 wks</div>
        </div>
        <div style="grid-column:1/-1;font-size:12px;font-weight:700;color:#5b6680;margin-top:6px;">Phase 2: integration</div>
        <div style="font-size:15px;font-weight:700;">Referral tracking</div>
        <div style="position:relative;height:32px;background:repeating-linear-gradient(to right,#dce2ec 0 1px,transparent 1px 20%);">
          <div style="position:absolute;left:60%;width:9%;top:5px;height:22px;border-radius:4px;background:#2b5bd7;color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;padding-left:8px;">2 d</div>
        </div>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="background:#0f1b33;color:#fff;border-radius:10px;padding:18px 20px;">
        <h3 style="font-size:12px;font-weight:700;color:#98a3ba;margin:0 0 6px 0;">Referral work alone</h3>
        <div style="font-size:40px;font-weight:800;">2–3 days</div>
      </div>
      <div style="border-left:4px solid #b8412f;padding:14px 16px;background:#f3f6fa;border-radius:0 8px 8px 0;">
        <h3 style="font-size:12px;font-weight:700;color:#5b6680;margin:0 0 6px 0;">Biggest unknown</h3>
        <p style="font-size:14px;margin:0;">What the scoring algorithm expects as input.</p>
      </div>
    </div>
  </div>
</div>""",
    },
]


def pick_example(slide_type: str, index: int) -> dict:
    """Round-robins within whichever examples fit this slide type, so a deck
    with several timeline/process slides doesn't reuse the same one."""
    matches = [example for example in EXAMPLES if slide_type in example["best_for"]]
    pool = matches or EXAMPLES
    return pool[index % len(pool)]
