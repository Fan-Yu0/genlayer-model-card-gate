# Portal submission draft

## Category

Builder -> Intelligent Contract

## Contribution date

Use the actual deployment date. Do not select a future date.

## Description (English, under 1,000 characters)

Model Card Conformance Gate is a standalone GenLayer primitive for AI model
procurement and marketplace admission. A provider registers a model card, a
system card, and a fixed disclosure policy. Anyone can trigger an assessment.
Validators independently fetch the official sources; an LLM extracts only the
risk tier, disclosure mask, and source consistency. The final decision is
computed by deterministic rules: conflicting evidence or an excessive risk tier
is rejected, a missing required disclosure is conditional, and a complete
submission is approved. The custom validator re-fetches the evidence and
compares the decision-bearing fields, so the LLM cannot approve a model by
formatting a friendly response. Other contracts can consume
`is_conformant(model_id)`. The repository includes source, tests, deployment
instructions, and a clear state model. It is intended to be reused by agent
registries, AI marketplaces, DAOs, and procurement contracts.

## Deployed evidence

- Public source repository:
  https://github.com/Fan-Yu0/genlayer-model-card-gate
- Contract: `0x20e1Bf44997dC3Bf89A776f95dB672fD712e1a5e`
- Contract Explorer:
  https://explorer-studio.genlayer.com/contracts/0x20e1Bf44997dC3Bf89A776f95dB672fD712e1a5e
- Deployment transaction:
  `0x0e68d96aa933d8d109d1d0c08e0235b87aebbb5c0d3f5ac68fe98e6a45d356b4`
- Deployment Explorer:
  https://explorer-studio.genlayer.com/tx/0x0e68d96aa933d8d109d1d0c08e0235b87aebbb5c0d3f5ac68fe98e6a45d356b4
- Deployment status: `FINALIZED`
- Successful assessment transaction:
  `0x854d5c8701115a698598bcf36e520038edf5665988612c3646095967c4f7d0ef`
- Assessment Explorer:
  https://explorer-studio.genlayer.com/tx/0x854d5c8701115a698598bcf36e520038edf5665988612c3646095967c4f7d0ef
- Assessment result: `MAJORITY_AGREE`, `ACCEPTED`
- Final decision: `APPROVED` (`decision = 1`, `round = 1`)

## First live example

Use these values in the deployed Studio contract:

```text
model_id: google/gemma-2-9b-it
model_card_url: https://huggingface.co/google/gemma-2-9b-it
system_card_url: https://arxiv.org/html/2408.00118
policy_url: https://www.nist.gov/itl/ai-risk-management-framework
required_tier: 3
required_mask: 15
```

Then call `assess("google/gemma-2-9b-it")`.

Add these after completing the live example:

1. Public GitHub repository URL.
2. Optional: the successful `register_model` transaction hash.
3. Optional: a short screen recording or public post showing the assessment.

## Submission notes

The contract is intentionally not a project/frontend submission. The core
deliverable is the reusable on-chain state machine and validator pattern. The
live example should use two real official documentation URLs; placeholder
domains are only used in tests.

## Reviewer checklist

- The contract has persistent state, role checks, and a clear lifecycle.
- The evidence extraction is separated from the deterministic policy engine.
- The custom validator independently re-fetches the same sources.
- The failure mode is fail-closed.
- Source, tests, docs, and deployment evidence are public.
