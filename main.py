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

    coordinator = Coordinator(
        repository=repo,
        customer_agent=CustomerAgent(repo),
        order_agent=OrderAgent(repo),
        payment_agent=PaymentAgent(repo),
        delivery_agent=DeliveryAgent(repo),
        policy_agent=PolicyAgent(),
        verifier_agent=VerifierAgent(),
    )

    input_dir = Path('input')
    output_dir = Path('output')

    if args.all:
        files = sorted(input_dir.glob('EC_*.json'))
    elif args.case:
        files = [input_dir / args.case]
    else:
        files = sorted(input_dir.glob('EC_*.json'))[:1]

    for case_file in files:
        case = load_case(case_file)
        try:
            result = coordinator.run(case)
            save_result(result, output_dir)
        except Exception as e:
            print(f"Error processing {case_file}: {e}")


if __name__ == '__main__':
    main()