---
name: article-generator
disable-model-invocation: true
description: "Generate beautifully styled Chinese long-form articles as HTML + PDF. Magazine-quality layout with dark hero, terminal blocks, comparison cards, timelines, pyramids, and info cards. User provides markdown-style content, agent generates the full article."
metadata: {"openclaw":{"requires":{"bins":["bash"]}}}
---

# Article Generator

Generate magazine-quality Chinese long-form articles with a distinctive visual style.

## When to Use

- User wants to write a new article / essay / deep-dive
- User provides markdown content and wants it styled
- User says "写文章", "生成文章", "做成PDF", "排版"

## Visual Style

The template uses a specific design language (see `references/` for the original):

- **Hero section**: Full-viewport dark background with animated grid, gold particles, gradient title
- **Section numbering**: Monospace `01`, `02`, etc. in accent red
- **Section titles**: Noto Serif SC, bold, with red underline bar
- **Body text**: Noto Sans SC, generous line-height (2x)
- **Quote blocks**: Left red border, parchment background, serif font
- **Terminal blocks**: Dark code-editor style with colored dots and green prompt
- **Big statements**: Dark card with green monospace glow text
- **Info cards**: Parchment background with gradient top border
- **Comparison cards**: Old (plain) vs New (gradient accent border) with arrow
- **Evolution timeline**: Vertical line with red/gold dots
- **Pyramid**: Layered width blocks, top = accent red, bottom = dim
- **Ending**: Dark section with serif text, gold highlights
- **Color palette**: ink (#1a1a1a), accent red (#c1272d), gold (#b8860b), navy (#1d3557)

## Workflow

### Step 1: Understand the Content

When the user provides content (markdown, outline, or plain text):
1. Identify the **title**, **subtitle**, and **tag line** for the hero
2. Break content into **numbered sections** (01, 02, 03...)
3. Identify opportunities for rich components:
   - Impactful quotes → `quote-block`
   - Code/commands → `terminal`
   - Key one-liners → `big-statement`
   - Explanatory asides → `info-card`
   - Before/after contrasts → `comparison`
   - Chronological progression → `evolution` timeline
   - Hierarchical concepts → `pyramid`
4. Write a **closing/ending** section
5. Add **footer** with title and year

### Step 2: Generate HTML

Use the template at `templates/article.html`:
- Replace `{{TITLE}}` with the article title
- Replace `{{BODY}}` with the full article body HTML
- All components use the CSS classes defined in the template
- For PDF compatibility: all sections should have `class="section"` (no JS animation needed)

### Step 3: Save and Convert

1. Save the HTML to the workspace: `output/<slug>.html`
2. Run the PDF conversion script:
   ```bash
   ./scripts/html-to-pdf.sh output/<slug>.html output/<slug>.pdf
   ```
3. Share both the HTML and PDF with the user

## Component Reference

### Hero
```html
<section class="hero">
  <div class="hero-grid"></div>
  <div class="hero-particles">
    <div class="particle"></div><!-- repeat 8x -->
  </div>
  <div class="hero-content">
    <p class="hero-tag">Tag · 标签</p>
    <h1 class="hero-title"><span class="highlight">高亮部分</span>的<br>标题</h1>
    <p class="hero-subtitle">副标题</p>
    <div class="hero-divider"></div>
  </div>
  <div class="scroll-hint">SCROLL</div>
</section>
```

### Section
```html
<div class="section">
  <div class="section-number">01</div>
  <div class="section-title">标题</div>
  <p>正文段落...</p>
</div>
```

### Quote Block
```html
<div class="quote-block">
  <span class="quote-mark">"</span>
  <p>引用文字</p>
</div>
```

### Terminal
```html
<div class="terminal">
  <div class="terminal-bar">
    <div class="terminal-dot r"></div>
    <div class="terminal-dot y"></div>
    <div class="terminal-dot g"></div>
    <span class="terminal-label">label</span>
  </div>
  <div class="terminal-body">
    <div><span class="prompt-symbol">❯ </span><span class="prompt-text">命令或代码</span></div>
    <div class="output">输出结果</div>
  </div>
</div>
```

### Big Statement
```html
<div class="big-statement">
  <p class="mono">核心金句</p>
</div>
```

### Info Card
```html
<div class="info-card">
  <div class="info-card-title">卡片标题</div>
  <p>卡片内容</p>
</div>
```

### Comparison
```html
<div class="comparison">
  <div class="comp-box old">
    <div class="label">旧</div>
    <div class="comp-title">旧方式</div>
    <div class="desc">描述</div>
  </div>
  <div class="comp-arrow">→</div>
  <div class="comp-box new">
    <div class="label">新</div>
    <div class="comp-title">新方式</div>
    <div class="desc">描述</div>
  </div>
</div>
```

### Evolution Timeline
```html
<div class="evolution">
  <div class="evo-item">
    <div class="era">时代</div>
    <div class="evo-title">标题</div>
    <div class="evo-desc">描述</div>
  </div>
  <!-- more items... last item gets gold styling automatically -->
</div>
```

### Pyramid
```html
<div class="pyramid">
  <div class="pyramid-level l1">顶层（最重要）</div>
  <div class="pyramid-level l2">第二层</div>
  <div class="pyramid-level l3">第三层</div>
  <div class="pyramid-level l4">底层（AI自动化）</div>
</div>
```

### Ending
```html
<section class="ending">
  <div class="ending-text">
    结语文字<span class="em">强调</span>和<span class="gold">金色高亮</span>。
  </div>
</section>
```

### Special text
- `<strong class="spell">金色强调词</strong>` — gold colored emphasis
- `<strong>普通强调</strong>` — standard bold dark emphasis

## Notes
- Template loads Google Fonts (Noto Serif SC, Noto Sans SC, JetBrains Mono) — needs internet for first render
- PDF generation uses Chrome headless with `--virtual-time-budget=5000` to wait for font loading
- Output directory: `output/` in skill directory (create if needed)
- Always generate both HTML (for web sharing) and PDF (for distribution)
