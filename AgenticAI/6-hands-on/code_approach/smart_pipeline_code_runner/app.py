import argparse
import json
import uuid
from pathlib import Path
from .tools.archive import restore, write_json


def main():
    parser = argparse.ArgumentParser(description='Verified sales workflow')
    parser.add_argument('input', nargs='?', help='Sales input folder')
    parser.add_argument('--workdir', default='smart_pipeline/work')
    parser.add_argument('--request', default='Combine compatible sales CSVs and summarize revenue.')
    parser.add_argument('--provider', help='LangChain provider, e.g. openai, anthropic, google_genai, ollama')
    parser.add_argument('--model', help='Model ID; defaults to gpt-4.1-mini for OpenAI')
    parser.add_argument('--base-url', help='Optional provider endpoint, e.g. an OpenAI-compatible server')
    parser.add_argument('--model-options', help='JSON object of provider-specific arguments')
    parser.add_argument('--offline', action='store_true', help='Use reference fixture instead of model-generated code')
    parser.add_argument('--resume', help='Resume an existing run ID')
    parser.add_argument('--restore', help='Restore originals from a run ID, without overwriting changed files')
    args = parser.parse_args()
    work = Path(args.workdir).resolve()
    if not args.input:
        parser.error('An input folder is required')
    source = Path(args.input).resolve()
    if not source.is_dir() or work.is_relative_to(source) or source.is_relative_to(work):
        parser.error('Input and work directories must be separate and non-nested')
    run_id = args.resume or args.restore or uuid.uuid4().hex
    if not run_id.isalnum():
        parser.error('Run IDs must be alphanumeric')
    run = work / 'runs' / run_id
    if args.restore:
        restore(run, source)
        print('Originals restored; archive copies retained.')
        return
    from langgraph.checkpoint.sqlite import SqliteSaver
    from .graph import build_graph
    model = None
    if not args.offline:
        from .models import ModelConfig, create_model
        try:
            model = create_model(ModelConfig.resolve(args.provider, args.model, args.base_url, args.model_options))
        except (ValueError, ImportError) as e:
            parser.error(str(e))
    if args.resume:
        settings = json.loads((run / 'settings.json').read_text())
        if settings != {'input': str(source), 'offline': args.offline}:
            parser.error('Resume must use the original input and offline setting')
    else:
        run.mkdir(parents=True, exist_ok=False)
        write_json(run / 'settings.json', {'input': str(source), 'offline': args.offline})
    state = dict(run_id=run_id, user_request=args.request, input_root=str(source), run_root=str(run),
                 execution_attempts=0, errors=[], archive_manifest=[], status='starting')
    config = {'configurable': {'thread_id': run_id}, 'recursion_limit': 40}
    with SqliteSaver.from_conn_string(str(work / 'checkpoints.sqlite')) as saver:
        graph = build_graph(model, work / 'archive', saver, args.offline)
        try:
            for update in graph.stream(None if args.resume else state, config):
                print(json.dumps(update, default=str))
        except Exception as e:
            write_json(run / 'failure.json', {'error': str(e), 'run_id': run_id})
            raise
        final = graph.get_state(config).values
        print('Reports:', run)
        if final.get('status') != 'complete':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
