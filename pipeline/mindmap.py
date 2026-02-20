"""Concept map generation using Claude API.

Analyzes a transcript and produces structured mind map output
in Markdown, HTML, and JSON formats.
"""

import json
import os
import html as html_mod

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

# Path to bundled vis-network library for self-contained HTML output
_VIS_NETWORK_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vis-network.min.js")

# Maximum transcript characters to send to Claude (to stay within context limits)
MAX_TRANSCRIPT_LENGTH = 100_000

SYSTEM_PROMPT = """You are an expert at analyzing educational and informational content \
and creating structured concept maps / mind maps. You extract key ideas, organize them \
hierarchically, and identify relationships between concepts."""

EXTRACTION_PROMPT = """\
Analyze the following transcript and create a structured concept map.

Extract:
- The central topic / main idea
- 5-8 main branches (key concepts or themes)
- 2-4 sub-nodes for each branch (details, examples, facts)
- Use meaningful, concise labels

Return ONLY valid JSON matching this exact schema (no other text):
{{
  "title": "string - central topic",
  "nodes": [
    {{
      "id": "string - unique id like 'n1', 'n1.1'",
      "label": "string - concise label",
      "parent": "string | null - parent node id, null for root",
      "level": 0,
      "color": "string - hex color code",
      "notes": "string - optional detail or explanation"
    }}
  ]
}}

Level 0 = root (one node: the central topic), level 1 = main branches, level 2 = sub-nodes.
Use a consistent color palette: assign the same color to a branch and all its children.
Use these colors for branches: #4A90D9, #E67E22, #2ECC71, #9B59B6, #E74C3C, #1ABC9C, #F39C12, #3498DB.

TRANSCRIPT:
{transcript}"""


def _call_claude(transcript: str) -> dict:
    """Send transcript to Claude and parse the JSON response."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Truncate very long transcripts
    if len(transcript) > MAX_TRANSCRIPT_LENGTH:
        transcript = transcript[:MAX_TRANSCRIPT_LENGTH] + "\n\n[...transcript truncated...]"

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT.format(transcript=transcript),
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # Extract JSON from response (handle possible markdown code blocks)
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        json_lines = []
        inside = False
        for line in lines:
            if line.strip().startswith("```") and not inside:
                inside = True
                continue
            if line.strip() == "```" and inside:
                break
            if inside:
                json_lines.append(line)
        response_text = "\n".join(json_lines)

    return json.loads(response_text)


def _generate_markdown(data: dict) -> str:
    """Generate a Markmap-compatible Markdown mind map."""
    lines = [f"# {data['title']}\n"]

    nodes_by_id = {n["id"]: n for n in data["nodes"]}
    children_of = {}
    for n in data["nodes"]:
        parent = n["parent"]
        if parent is not None:
            children_of.setdefault(parent, []).append(n)

    def _render(node_id: str, depth: int):
        node = nodes_by_id[node_id]
        if depth > 0:  # Skip root (already rendered as H1)
            indent = "  " * (depth - 1)
            lines.append(f"{indent}- **{node['label']}**")
            if node.get("notes"):
                lines.append(f"{indent}  - {node['notes']}")
        for child in children_of.get(node_id, []):
            _render(child["id"], depth + 1)

    # Find root node
    root = next((n for n in data["nodes"] if n["parent"] is None), None)
    if root:
        _render(root["id"], 0)

    return "\n".join(lines) + "\n"


def _generate_html(data: dict) -> str:
    """Generate a self-contained interactive HTML mind map using vis-network."""
    nodes_js = []
    edges_js = []

    for n in data["nodes"]:
        font_size = {0: 24, 1: 18}.get(n["level"], 14)
        shape = "ellipse" if n["level"] == 0 else "box"
        node_obj = {
            "id": n["id"],
            "label": n["label"],
            "color": {
                "background": n.get("color", "#4A90D9"),
                "border": n.get("color", "#4A90D9"),
                "highlight": {"background": "#FFD700", "border": "#FFA500"},
            },
            "font": {"size": font_size, "color": "#FFFFFF", "face": "Arial"},
            "shape": shape,
            "margin": 12,
            "shadow": True,
        }
        if n.get("notes"):
            node_obj["title"] = html_mod.escape(n["notes"])
        nodes_js.append(node_obj)

        if n["parent"] is not None:
            edges_js.append({
                "from": n["parent"],
                "to": n["id"],
                "color": {"color": "#888888", "highlight": "#FFA500"},
                "width": 2,
                "smooth": {"type": "cubicBezier"},
            })

    title_escaped = html_mod.escape(data["title"])
    nodes_json = json.dumps(nodes_js, indent=2)
    edges_json = json.dumps(edges_js, indent=2)

    # Load vis-network library for inline embedding
    with open(_VIS_NETWORK_PATH, "r", encoding="utf-8") as f:
        vis_network_js = f.read()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_escaped} - VideoMind Concept Map</title>
<script>{vis_network_js}</script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #1a1a2e;
    color: #eee;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }}
  header {{
    padding: 16px 24px;
    background: #16213e;
    border-bottom: 2px solid #0f3460;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  header h1 {{
    font-size: 1.3rem;
    font-weight: 600;
  }}
  header .badge {{
    background: #e94560;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
  }}
  #network {{
    flex: 1;
    width: 100%;
  }}
  .tooltip {{
    font-size: 0.85rem;
    max-width: 300px;
  }}
</style>
</head>
<body>
<header>
  <h1>{title_escaped}</h1>
  <span class="badge">VideoMind</span>
</header>
<div id="network"></div>
<script>
var nodes = new vis.DataSet({nodes_json});
var edges = new vis.DataSet({edges_json});
var container = document.getElementById("network");
var data = {{ nodes: nodes, edges: edges }};
var options = {{
  physics: {{
    solver: "forceAtlas2Based",
    forceAtlas2Based: {{
      gravitationalConstant: -80,
      centralGravity: 0.01,
      springLength: 150,
      springConstant: 0.04,
      damping: 0.4
    }},
    stabilization: {{ iterations: 200 }}
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 200,
    zoomView: true,
    dragView: true
  }},
  layout: {{
    improvedLayout: true
  }}
}};
var network = new vis.Network(container, data, options);
network.once("stabilizationIterationsDone", function() {{
  network.fit({{ animation: true }});
}});
</script>
</body>
</html>"""


def generate_mindmap(
    transcript: str,
    output_dir: str,
    formats: str = "all",
) -> dict:
    """Generate concept map files from a transcript.

    Args:
        transcript: The full transcript text.
        output_dir: Directory to write output files to.
        formats: "all", "html", "md", or "json".

    Returns:
        {"json_path": str, "md_path": str, "html_path": str, "data": dict}
    """
    os.makedirs(output_dir, exist_ok=True)

    print("  Analyzing transcript with Claude...")
    data = _call_claude(transcript)

    paths = {}

    if formats in ("all", "json"):
        json_path = os.path.join(output_dir, "mindmap.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        paths["json_path"] = json_path
        print(f"  Saved: {json_path}")

    if formats in ("all", "md"):
        md_content = _generate_markdown(data)
        md_path = os.path.join(output_dir, "mindmap.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        paths["md_path"] = md_path
        print(f"  Saved: {md_path}")

    if formats in ("all", "html"):
        html_content = _generate_html(data)
        html_path = os.path.join(output_dir, "mindmap.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        paths["html_path"] = html_path
        print(f"  Saved: {html_path}")

    paths["data"] = data
    return paths
