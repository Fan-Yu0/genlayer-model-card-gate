# Model Card Conformance Gate

A standalone GenLayer Intelligent Contract primitive for evidence-based AI
model procurement and marketplace admission.

Repository: <https://github.com/Fan-Yu0/genlayer-model-card-gate>

## What it does

A model provider registers two official evidence sources:

- a model card;
- a system card.

The provider also fixes a buyer policy URL, a maximum acceptable risk tier, and
a bitmask of disclosures the buyer requires. Anyone may then trigger
`assess(model_id)`.

GenLayer validators independently fetch the two official cards and the policy.
An LLM extracts only structured evidence:

- risk tier;
- disclosure bitmask;
- whether the two official sources are consistent;
- a short evidence summary.

The contract then computes the final decision deterministically:

| Condition | Decision |
| --- | --- |
| Sources conflict or are insufficient | `REJECTED` |
| Extracted risk tier exceeds the buyer ceiling | `REJECTED` |
| Required disclosure is missing | `CONDITIONAL` |
| All checks pass | `APPROVED` |

The LLM never chooses the final approval. It only normalizes evidence, and the
custom validator independently re-fetches the same sources and compares the
decision-bearing fields. A disagreement produces no state change rather than a
silent approval.

## Why this is a reusable primitive

- The contract is useful without a frontend.
- Any marketplace, procurement contract, DAO, or agent registry can query
  `is_conformant(model_id)`.
- The policy is data, not hard-coded business logic.
- The evidence extraction and the deterministic policy engine are separated.
- The same pattern can be forked for datasets, APIs, or agent manifests by
  changing the disclosure bits and evidence prompt.

## State machine

```text
DRAFT --assess--> ASSESSED --assess--> ASSESSED
  |                  |
  +------withdraw----+--> WITHDRAWN
```

`assess` is permissionless: the evidence and rules are public, so any caller
can request a fresh evaluation. `register_model` and `withdraw` are restricted
to the address that registered the model.

## Consensus design

The non-deterministic block performs three web reads and one structured LLM
extraction. The leader returns:

```json
{
  "risk_tier": 2,
  "disclosure_mask": 127,
  "source_consistency": "consistent",
  "summary": "short evidence summary"
}
```

The validator independently repeats the task and compares the outcomes that
actually affect the decision: whether the risk tier is within the buyer
ceiling, whether every required disclosure bit is present, and whether the
sources are consistent. `summary` and irrelevant disclosure bits are not
compared. The accepted structured result is returned to deterministic code,
where the disclosure gap and final decision are calculated.

This avoids two weak patterns:

1. trusting a leader's JSON shape without checking the evidence;
2. asking an LLM to make the final business decision directly.

## Disclosure bits

| Bit | Field |
| --- | --- |
| 1 | intended use |
| 2 | limitations |
| 4 | training data |
| 8 | evaluation |
| 16 | human oversight |
| 32 | security |
| 64 | environmental impact |
| 127 | all seven fields |

Call `disclosure_bits()` on the deployed contract for the authoritative values.

## Repository layout

```text
contracts/model_card_gate.py       Intelligent Contract
tests/direct/test_model_card_gate.py
deploy/deployScript.ts
gltest.config.yaml
SUBMISSION.md                      Portal form draft
```

## Local verification

```shell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
genvm-lint check contracts/model_card_gate.py
pytest tests/direct/ -v
```

On a machine where Python is not on `PATH`, use the bundled Python runtime or
run the contract in GenLayer Studio. The pinned test versions in
`requirements.txt` are the versions used for the included direct tests.
`tests/direct/conftest.py` contains a small Windows-only cleanup shim for a
`gltest-direct` temporary-file issue; it does not affect the contract.

## Deploy

### Studio

1. Open <https://studio.genlayer.com/>.
2. Select the current GenLayer testnet shown in Studio.
3. Create a new contract, paste `contracts/model_card_gate.py`, and deploy with
   no constructor arguments.
4. Call `register_model` with a real public model card and system card.
5. Call `assess(model_id)`.
6. Save the contract address and the deployment transaction hash.

### CLI

```shell
npm install
genlayer network
genlayer deploy
```

## Suggested live example

Register a public model card from Hugging Face and its corresponding official
documentation. Use a real procurement policy or a small public policy file that
states the required disclosures. Avoid placeholder URLs: reviewers need to be
able to reproduce the assessment.

## Current deployment

- Contract: `0x20e1Bf44997dC3Bf89A776f95dB672fD712e1a5e`
- Network: GenLayer Studio stable (`studionet`)
- Deployment status: `FINALIZED`
- Explorer:
  https://explorer-studio.genlayer.com/contracts/0x20e1Bf44997dC3Bf89A776f95dB672fD712e1a5e
- Live assessment: `google/gemma-2-9b-it`
- Assessment transaction:
  https://explorer-studio.genlayer.com/tx/0x854d5c8701115a698598bcf36e520038edf5665988612c3646095967c4f7d0ef
- Assessment result: `MAJORITY_AGREE`, `ACCEPTED`, decision `APPROVED`

## Security notes

- Only HTTPS evidence URLs are accepted.
- The two official cards are fetched independently on every assessment.
- Conflicting or incomplete evidence fails closed.
- The final decision is deterministic; the LLM cannot approve a model by
  returning a friendly summary.
- This contract records a procurement signal. It is not a legal certification
  or a substitute for a regulator's decision.
