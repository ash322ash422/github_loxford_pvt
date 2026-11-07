"""Export the real compiled LangGraph without model calls or external renderers."""
import argparse
from html import escape
from pathlib import Path
from .graph import build_graph


def export_workflow(output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    graph = build_graph(None, output / 'unused_archive').get_graph()
    (output / 'workflow.mmd').write_text(graph.draw_mermaid(), encoding='utf-8')
    # Draw the compiled graph's nodes and edges locally as a standalone SVG.
    # Positions describe presentation only; topology comes from get_graph().
    positions = {'__start__': (320, 80), 'scan': (320, 165), 'profile': (320, 250),
                 'plan': (320, 335), 'generate': (320, 420), 'execute': (320, 505),
                 'validate': (320, 590), 'archive': (320, 705), 'report': (320, 810),
                 '__end__': (320, 895)}
    labels = {'__start__': 'Start', '__end__': 'End', 'scan': 'Scan + snapshot inputs',
              'profile': 'Profile CSVs + inspect context', 'plan': 'Create sales processing plan',
              'generate': 'Generate / repair Python code', 'execute': 'Execute in Docker',
              'validate': 'Validate records + totals', 'archive': 'Archive eligible originals',
              'report': 'Write report + manifest'}
    if set(graph.nodes) != set(positions):
        raise ValueError('Graph nodes changed; update the SVG layout in draw_workflow.py')
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="940" height="980" viewBox="0 0 940 980">',
             '<title>Smart Pipeline LangGraph workflow</title>',
             '<desc>Compiled graph with a bounded code repair loop and trusted archive stage.</desc>',
             '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#526681"/></marker></defs>',
             '<rect width="940" height="980" fill="#f5f8fc"/>',
             '<g font-family="Segoe UI,Arial,sans-serif" font-size="15" fill="#17304d">',
             '<text x="35" y="32" font-size="23" font-weight="bold">Smart Pipeline: compiled LangGraph workflow</text>']
    def caption(x, y, text):
        parts.append(f'<text x="{x}" y="{y}" font-size="13">{escape(text)}</text>')
    for edge in graph.edges:
        x, y = positions[edge.source]
        tx, ty = positions[edge.target]
        if (edge.source, edge.target) == ('validate', 'generate'):
            path = f'M {x-150} {y} H 45 V {ty} H {tx-150}'
            caption(52, 465, 'Invalid: repair')
            caption(52, 485, 'Max 2 repairs')
            caption(52, 545, 'Live mode only')
        elif (edge.source, edge.target) == ('validate', 'report'):
            path = f'M {x+150} {y} H 710 V {ty} H {tx+150}'
            caption(720, 635, 'Invalid; attempts exhausted')
            caption(720, 655, 'or offline execution failed')
            caption(720, 675, 'No archive')
        else:
            path = f'M {x} {y+25} L {tx} {ty-25}'
        parts.append(f'<path d="{path}" fill="none" stroke="#526681" stroke-width="2" marker-end="url(#arrow)"/>')
    caption(335, 655, 'Valid')
    for name, (x, y) in positions.items():
        color = '#dbeafe' if name == 'generate' else '#ffffff'
        parts.append(f'<rect x="{x-150}" y="{y-25}" width="300" height="50" rx="12" fill="{color}" stroke="#526681"/>')
        parts.append(f'<text x="{x}" y="{y+5}" text-anchor="middle">{escape(labels[name])}</text>')
    caption(35, 955, 'Topology exported from build_graph().get_graph(); drawing does not run the workflow.')
    parts.append('</g></svg>')
    (output / 'workflow.svg').write_text('\n'.join(parts), encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', default='smart_pipeline/docs')
    args = parser.parse_args()
    print('Workflow diagrams saved to:', export_workflow(args.output_dir).resolve())


if __name__ == '__main__':
    main()
