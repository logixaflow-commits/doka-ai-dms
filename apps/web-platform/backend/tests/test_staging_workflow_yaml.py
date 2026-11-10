from pathlib import Path
import yaml

def test_staging_workflow_yaml_parses_and_has_no_feature_branch_triggers():
    path = Path(__file__).resolve().parents[4] / '.github' / 'workflows' / 'cloudflare-worker-staging-deploy.yml'
    text = path.read_text(encoding='utf-8')
    workflow = yaml.safe_load(text)
    triggers = workflow.get('on', workflow.get(True, {}))
    assert 'workflow_dispatch' in triggers
    assert 'branches:' not in text
    assert 'fix/staging-rpc-security-parity' not in text
    assert 'fix/cloudinary-private-derivatives' not in text
    assert 'environment:' in text and 'name: staging' in text
