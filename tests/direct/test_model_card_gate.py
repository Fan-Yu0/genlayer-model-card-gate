import json

from tests.direct.conftest import to_hex


MODEL_ID = "acme/vision-1"
MODEL_CARD = "https://docs.example.com/acme/vision-1/model-card"
SYSTEM_CARD = "https://docs.example.com/acme/vision-1/system-card"
POLICY = "https://buyer.example.com/ai-procurement-policy"


def _mock_evidence(vm, payload):
    vm.mock_web(
        r".*docs\.example\.com/acme/vision-1/model-card.*",
        {"status": 200, "body": "Intended use: classification. Limitations: synthetic data."},
    )
    vm.mock_web(
        r".*docs\.example\.com/acme/vision-1/system-card.*",
        {"status": 200, "body": "Evaluation and security review completed."},
    )
    vm.mock_web(
        r".*buyer\.example\.com/ai-procurement-policy.*",
        {"status": 200, "body": "High-risk systems require human oversight."},
    )
    vm.mock_llm(r".*MODEL CARD AUDIT.*", json.dumps(payload))


def _register(contract, vm, provider, required_tier=3, required_mask=127):
    vm.sender = provider
    contract.register_model(
        MODEL_ID,
        MODEL_CARD,
        SYSTEM_CARD,
        POLICY,
        required_tier,
        required_mask,
    )


def test_approves_when_all_required_disclosures_are_present(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice)

    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 2,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": True,
                "security": True,
                "environmental_impact": True,
            },
            "source_consistency": "consistent",
            "summary": "Both official cards disclose every required field.",
        },
    )
    contract.assess(MODEL_ID)

    result = contract.get_assessment(MODEL_ID)
    assert result["state"] == 1
    assert result["decision"] == 1
    assert result["risk_tier"] == 2
    assert result["missing_mask"] == 0
    assert result["round"] == 1
    assert contract.is_conformant(MODEL_ID) is True


def test_marks_conditional_when_a_disclosure_is_missing(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice)

    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 2,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": True,
                "security": True,
                "environmental_impact": False,
            },
            "source_consistency": "consistent",
            "summary": "Environmental impact is not documented.",
        },
    )
    contract.assess(MODEL_ID)

    result = contract.get_assessment(MODEL_ID)
    assert result["decision"] == 2
    assert result["missing_mask"] == 64
    assert contract.is_conformant(MODEL_ID) is False


def test_rejects_when_source_cards_conflict(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice)

    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 2,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": True,
                "security": True,
                "environmental_impact": True,
            },
            "source_consistency": "conflicting",
            "summary": "The cards disagree about human oversight.",
        },
    )
    contract.assess(MODEL_ID)

    result = contract.get_assessment(MODEL_ID)
    assert result["decision"] == 3
    assert result["source_consistency"] == "conflicting"


def test_rejects_risk_above_the_buyer_ceiling(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice, required_tier=2)

    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 3,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": True,
                "security": True,
                "environmental_impact": True,
            },
            "source_consistency": "consistent",
            "summary": "The model is high risk.",
        },
    )
    contract.assess(MODEL_ID)

    assert contract.get_assessment(MODEL_ID)["decision"] == 3


def test_only_provider_can_withdraw(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice)

    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("only the provider can withdraw"):
        contract.withdraw(MODEL_ID)

    direct_vm.sender = direct_alice
    contract.withdraw(MODEL_ID)
    assert contract.get_assessment(MODEL_ID)["state"] == 2
    assert contract.is_conformant(MODEL_ID) is False


def test_duplicate_model_id_is_rejected(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice)

    with direct_vm.expect_revert("model_id already registered"):
        contract.register_model(
            MODEL_ID,
            MODEL_CARD,
            SYSTEM_CARD,
            POLICY,
            3,
            127,
        )


def test_unknown_model_is_not_conformant(direct_deploy):
    contract = direct_deploy("contracts/model_card_gate.py")
    assert contract.is_conformant("unknown/model") is False
    assert contract.get_assessment("unknown/model") == {}


def test_validator_accepts_matching_evidence(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice)

    payload = {
        "risk_tier": 2,
        "disclosures": {
            "intended_use": True,
            "limitations": True,
            "training_data": True,
            "evaluation": True,
            "human_oversight": True,
            "security": True,
            "environmental_impact": True,
        },
        "source_consistency": "consistent",
        "summary": "All required disclosures are present.",
    }
    _mock_evidence(direct_vm, payload)
    contract.assess(MODEL_ID)

    assert direct_vm.run_validator() is True


def test_validator_rejects_changed_evidence(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice)

    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 2,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": True,
                "security": True,
                "environmental_impact": True,
            },
            "source_consistency": "consistent",
            "summary": "Leader evidence.",
        },
    )
    contract.assess(MODEL_ID)

    direct_vm.clear_mocks()
    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 4,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": True,
                "security": True,
                "environmental_impact": True,
            },
            "source_consistency": "consistent",
            "summary": "Validator sees a different risk tier.",
        },
    )

    assert direct_vm.run_validator() is False


def test_validator_tolerates_risk_tier_variation_within_ceiling(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice, required_mask=15)

    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 2,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": False,
                "security": False,
                "environmental_impact": False,
            },
            "source_consistency": "consistent",
            "summary": "Leader sees limited risk.",
        },
    )
    contract.assess(MODEL_ID)

    direct_vm.clear_mocks()
    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 3,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": True,
                "security": True,
                "environmental_impact": False,
            },
            "source_consistency": "consistent",
            "summary": "Validator sees high risk but the same required facts.",
        },
    )

    assert direct_vm.run_validator() is True


def test_validator_rejects_a_required_disclosure_difference(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/model_card_gate.py")
    _register(contract, direct_vm, direct_alice, required_mask=15)

    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 3,
            "disclosures": {
                "intended_use": True,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": False,
                "security": False,
                "environmental_impact": False,
            },
            "source_consistency": "consistent",
            "summary": "All required facts are present.",
        },
    )
    contract.assess(MODEL_ID)

    direct_vm.clear_mocks()
    _mock_evidence(
        direct_vm,
        {
            "risk_tier": 3,
            "disclosures": {
                "intended_use": False,
                "limitations": True,
                "training_data": True,
                "evaluation": True,
                "human_oversight": False,
                "security": False,
                "environmental_impact": False,
            },
            "source_consistency": "consistent",
            "summary": "Intended use is missing.",
        },
    )

    assert direct_vm.run_validator() is False
