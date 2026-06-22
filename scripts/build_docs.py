import os
import re

DOCS_STRUCTURE = [
    ("Master Navigation Index", "NAVIGATION.html"),
    ("PrefixIQ Project Report", "project_report.html"),
    ("Dataset Specification", "dataset.html"),
]

PRIVATE_DOCS_STRUCTURE = [
    ("Back to Main Docs", "../../docs/html/NAVIGATION.html"),
    ("PrefixIQ System Handbook", "PrefixIQ-System-Handbook.html"),
    ("Viva Mock Questions Guide", "viva.html"),
    ("Quick Revision Flashcards", "flashcards.html"),
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - PrefixIQ</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        zinc: {{
                            850: '#1e1e24',
                            950: '#09090b',
                        }},
                        violet: {{
                            950: '#1e1b4b',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <!-- Prism.js Syntax Highlighting -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <!-- Mermaid.js for Diagrams -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'dark',
            securityLevel: 'loose'
        }});
    </script>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #09090b;
        }}
        code, pre {{
            font-family: 'JetBrains Mono', monospace !important;
        }}
        /* Markdown table styling */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #27272a;
            text-align: left;
        }}
        th {{
            background-color: #18181b;
            color: #ffffff;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: rgba(39, 39, 42, 0.2);
        }}
    </style>
</head>
<body class="text-zinc-300">
    <div class="flex min-h-screen">
        <!-- Sidebar Navigation -->
        <aside class="w-80 bg-zinc-950 border-r border-zinc-800 p-6 flex flex-col justify-between hidden md:flex">
            <div>
                <div class="flex items-center gap-2 mb-8">
                    <span class="w-3 h-3 rounded-full bg-violet-500 animate-pulse"></span>
                    <span class="text-white font-extrabold text-xl tracking-tight">Prefix<span class="text-violet-400">IQ</span></span>
                    <span class="text-[10px] text-zinc-500 border border-zinc-800 px-1.5 py-0.5 rounded">Docs</span>
                </div>
                <nav class="space-y-1.5">
                    <span class="text-[10px] text-zinc-500 uppercase font-bold tracking-wider block mb-2 px-3">Documentation Pages</span>
                    {sidebar}
                </nav>
            </div>
            <div class="pt-6 border-t border-zinc-900 text-xs text-zinc-650">
                PrefixIQ System Design Handbook
            </div>
        </aside>

        <!-- Main Content Area -->
        <main class="flex-1 p-6 md:p-12 overflow-y-auto max-w-5xl mx-auto w-full">
            <!-- Mobile Header -->
            <div class="flex items-center justify-between pb-6 mb-8 border-b border-zinc-900 md:hidden">
                <span class="text-white font-extrabold text-lg">Prefix<span class="text-violet-400">IQ</span> Docs</span>
                <span class="text-xs text-zinc-500">Menu</span>
            </div>

            <!-- Page Article Content -->
            <article class="prose prose-invert max-w-none space-y-6">
                {content}
            </article>
        </main>
    </div>

    <!-- Prism.js Script -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
</body>
</html>
"""

def parse_markdown(md_text):
    """
    Translates basic markdown syntax to HTML.
    Includes custom headers, lists, code highlighting, tables, and alerts.
    """
    html = md_text

    # Replace local file links to HTML links
    html = re.sub(r'\[([^\]]+)\]\(file:///[^)]+/docs/([^)]+)\.md\)', r'<a href="\2.html" class="text-violet-400 hover:underline">\1</a>', html)
    html = re.sub(r'\[([^\]]+)\]\(file:///[^)]+/private-docs/([^)]+)\.md\)', r'<a href="../../private-docs/html/\2.html" class="text-violet-400 hover:underline">\1</a>', html)
    html = re.sub(r'\[([^\]]+)\]\(file:///[^)]+\)', r'<span class="text-zinc-200 font-mono">\1</span>', html)

    # 1. Blockquotes and GitHub style Alerts
    # > [!IMPORTANT]
    def replace_alert(match):
        alert_type = match.group(1).upper()
        content = match.group(2).strip()
        color_class = "border-violet-650 bg-violet-950/20 text-violet-300" if alert_type == "IMPORTANT" else "border-zinc-700 bg-zinc-900/40 text-zinc-300"
        return f'<div class="border-l-4 p-4 rounded-r-lg my-6 {color_class}"><strong class="block text-xs uppercase tracking-wide mb-1 text-white">{alert_type}</strong>{content}</div>'
    
    html = re.sub(r'^>\s*\[!([a-zA-Z]+)\]\s*\n((?:^>.*$\n?)+)', lambda m: replace_alert(MagicMock(group=lambda i: m.group(i).replace('>', '').strip() if i==1 else m.group(i).replace('\n> ', '\n').replace('> ', ''))), html, flags=re.MULTILINE)
    # Simple blockquotes
    html = re.sub(r'^>\s*(?!\[!)(.+)$', r'<blockquote class="border-l-4 border-zinc-700 pl-4 py-1.5 italic my-4 text-zinc-400">\1</blockquote>', html, flags=re.MULTILINE)

    # 2. Code blocks (Mermaid vs standard languages)
    # ```mermaid ... ```
    html = re.sub(r'```mermaid\s*\n(.*?)\n```', r'<div class="mermaid my-6 bg-zinc-950 p-6 rounded-xl border border-zinc-900">\1</div>', html, flags=re.DOTALL)
    # Regular ```python ... ```
    html = re.sub(r'```([a-zA-Z0-9+#-]+)\s*\n(.*?)\n```', r'<pre class="bg-zinc-950 p-5 rounded-xl border border-zinc-900 overflow-x-auto my-6"><code class="language-\1">\2</code></pre>', html, flags=re.DOTALL)

    # 3. Inline code
    html = re.sub(r'`([^`\n]+)`', r'<code class="bg-zinc-900 px-1.5 py-0.5 rounded text-zinc-100 font-mono text-sm border border-zinc-800">\1</code>', html)

    # 4. Headers: #, ##, ###, ####
    html = re.sub(r'^#\s+(.+)$', r'<h1 class="text-3xl font-extrabold text-white tracking-tight mt-8 mb-4 border-b border-zinc-900 pb-2">\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^##\s+(.+)$', r'<h2 class="text-2xl font-bold text-white tracking-tight mt-8 mb-4 border-b border-zinc-900/50 pb-1.5">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^###\s+(.+)$', r'<h3 class="text-xl font-semibold text-white tracking-tight mt-6 mb-3">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^####\s+(.+)$', r'<h4 class="text-base font-semibold text-zinc-100 tracking-tight mt-4 mb-2">\1</h4>', html, flags=re.MULTILINE)

    # 5. Lists (unordered and ordered)
    # Bullet points
    html = re.sub(r'^\s*-\s+(.+)$', r'<li class="list-disc ml-6 py-0.5 text-[15px]">\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'((?:<li class="list-disc ml-6 py-0.5 text-\[15px\]">.*</li>\n?)+)', r'<ul class="my-4 space-y-1">\1</ul>', html)
    # Checked lists [ ] or [x]
    html = html.replace('`[ ]`', '<span class="inline-block w-4 h-4 rounded border border-zinc-700 bg-zinc-900 mr-2"></span>')
    html = html.replace('`[x]`', '<span class="inline-block w-4 h-4 rounded border border-violet-600 bg-violet-950 text-violet-300 flex items-center justify-center text-[10px] mr-2">✓</span>')

    # 6. Tables
    def table_converter(match):
        table_lines = match.group(0).strip().split('\n')
        if len(table_lines) < 2:
            return match.group(0)
        
        headers = [h.strip() for h in table_lines[0].split('|')[1:-1]]
        html_table = ['<div class="overflow-x-auto my-6 border border-zinc-800 rounded-xl"><table class="min-w-full"><thead><tr>']
        for h in headers:
            html_table.append(f'<th>{h}</th>')
        html_table.append('</tr></thead><tbody>')
        
        for row in table_lines[2:]:
            cols = [c.strip() for c in row.split('|')[1:-1]]
            html_table.append('<tr>')
            for col in cols:
                html_table.append(f'<td>{col}</td>')
            html_table.append('</tr>')
        
        html_table.append('</tbody></table></div>')
        return '\n'.join(html_table)

    html = re.sub(r'((?:^\|.+$\n?)+)', table_converter, html, flags=re.MULTILINE)

    # Bold and Italic formatting
    html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)

    # Wrap lone paragraphs
    paragraphs = []
    for block in html.split('\n\n'):
        block = block.strip()
        if not block:
            continue
        if block.startswith('<h') or block.startswith('<ul') or block.startswith('<div') or block.startswith('<blockquote') or block.startswith('<pre'):
            paragraphs.append(block)
        else:
            paragraphs.append(f'<p class="leading-relaxed text-[15px] my-3">{block}</p>')
    
    return '\n'.join(paragraphs)

class MagicMock:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def build_docs():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.join(script_dir, "..")
    
    # 1. Compile docs/ folder markdown files
    docs_dir = os.path.join(root_dir, "docs")
    html_docs_dir = os.path.join(docs_dir, "html")
    os.makedirs(html_docs_dir, exist_ok=True)

    # Generate Sidebar HTML for public docs
    sidebar_public = []
    for label, filename in DOCS_STRUCTURE:
        sidebar_public.append(
            f'<a href="{filename}" class="flex items-center px-3 py-2 text-sm font-semibold rounded-lg text-zinc-400 hover:bg-zinc-900 hover:text-white transition-colors">{label}</a>'
        )
    sidebar_public_html = "\n".join(sidebar_public)

    print("Building local submission documentation pages...")
    for label, filename in DOCS_STRUCTURE:
        md_name = filename.replace(".html", ".md")
        md_path = os.path.join(docs_dir, md_name)
        if not os.path.exists(md_path):
            continue
        
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
            
        parsed_html = parse_markdown(md_content)
        full_html = HTML_TEMPLATE.format(
            title=label,
            sidebar=sidebar_public_html,
            content=parsed_html
        )
        
        out_path = os.path.join(html_docs_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f_out:
            f_out.write(full_html)
        print(f"  Compiled: {md_name} -> docs/html/{filename}")

    # 2. Compile private-docs/ folder markdown files
    priv_docs_dir = os.path.join(root_dir, "private-docs")
    html_priv_docs_dir = os.path.join(priv_docs_dir, "html")
    os.makedirs(html_priv_docs_dir, exist_ok=True)

    sidebar_private = []
    for label, filename in PRIVATE_DOCS_STRUCTURE:
        sidebar_private.append(
            f'<a href="{filename}" class="flex items-center px-3 py-2 text-sm font-semibold rounded-lg text-zinc-400 hover:bg-zinc-900 hover:text-white transition-colors">{label}</a>'
        )
    sidebar_private_html = "\n".join(sidebar_private)

    print("Building private documentation pages...")
    for label, filename in PRIVATE_DOCS_STRUCTURE:
        # Ignore back links
        if filename.startswith("../"):
            continue
            
        md_name = filename.replace(".html", ".md")
        md_path = os.path.join(priv_docs_dir, md_name)
        if not os.path.exists(md_path):
            continue
            
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
            
        parsed_html = parse_markdown(md_content)
        full_html = HTML_TEMPLATE.format(
            title=label,
            sidebar=sidebar_private_html,
            content=parsed_html
        )
        
        out_path = os.path.join(html_priv_docs_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f_out:
            f_out.write(full_html)
        print(f"  Compiled: {md_name} -> private-docs/html/{filename}")

    print("Docs compilation complete. You can open any HTML page directly in your browser!")

if __name__ == "__main__":
    build_docs()
