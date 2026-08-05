import argparse
import json
from pathlib import Path
from services.data_loader import DataLoader
from services.repository import Repository
from agents.customer_agent import CustomerAgent
from agents.order_agent import OrderAgent
from agents.payment_agent import PaymentAgent
from agents.delivery_agent import DeliveryAgent
from agents.policy_agent import PolicyAgent
from agents.verifier_agent import VerifierAgent
from agents.coordinator import Coordinator


def load_config():
    return {}


def build_repositories(db: DataLoader):
    return Repository(db)


def load_case(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_result(result: dict, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    case_id = result.get('case_id')
    path = out_dir / f"{case_id}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--case', type=str, help='case file name in input folder')
    args = parser.parse_args()

    db = DataLoader('data')
    repo = build_repositories(db)

    input_dir = Path('input')
    output_dir = Path('output')

    if args.all:
        files = sorted(input_dir.glob('EC_*.json'))
    elif args.case:
        files = [input_dir / args.case]
    else:
        files = sorted(input_dir.glob('EC_*.json'))[:1]

    trace_file = Path('trace.jsonl')
    # clear old trace file
    if trace_file.exists():
        trace_file.unlink()

    def process_case(case_file):
        case = load_case(case_file)
        # Create fresh agents per thread to be safe if they ever held state (they don't currently, but safe practice)
        coordinator = Coordinator(
            repository=repo,
            customer_agent=CustomerAgent(repo, use_llm=False),
            order_agent=OrderAgent(repo, use_llm=False),
            payment_agent=PaymentAgent(repo, use_llm=False),
            delivery_agent=DeliveryAgent(repo, use_llm=False),
            policy_agent=PolicyAgent(use_llm=False),
            verifier_agent=VerifierAgent(use_llm=False),
        )
        try:
            result = coordinator.run(case)
            save_result(result, output_dir)
            with open(trace_file, 'a', encoding='utf-8') as tf:
                trace_obj = {"input": case, "output": result}
                tf.write(json.dumps(trace_obj, ensure_ascii=False) + '\n')
            print(f"Success: {case_file.name}")
        except Exception as e:
            print(f"Error processing {case_file.name}: {e}")

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_case, files)


if __name__ == '__main__':
    main()