from services.data_loader import DataLoader

def main():
    config = load_config()

    db = DataLoader("data/")
    repos = build_repositories(db)

    coordinator = Coordinator(
        customer_agent=CustomerAgent(repos),
        order_agent=OrderAgent(repos),
        payment_agent=PaymentAgent(repos),
        delivery_agent=DeliveryAgent(repos),
        policy_agent=PolicyAgent(),
        verifier_agent=VerifierAgent(),
    )

    for case_file in Path("input").glob("*.json"):
        case = load_case(case_file)
        result = coordinator.run(case)
        save_result(result)

    save_trace()
    save_metadata()