# Configuration

* Scenario definitions (fault and attack injections, parameters): `src/pbti/scenarios.py` (`SCENARIOS`).
* Testbed defaults (topology, network, buffering): `src/pbti/sim.py` (`WorldConfig`, `NetConfig`).
* Verifier defaults (ticks, checkpoints, status refresh): `src/pbti/verifier.py` (`VerifierConfig`).
* Admission-policy parameters (horizons, windows, grace): `src/pbti/policy.py` (`DEFAULT_PARAMS`); an example policy
  document is in `policies/admission_policy.example.json`.
* Campaign matrices (scenarios × pipelines × seeds; ablations; revocation sweep; tamper audits):
  `experiments/run_campaign.py` (`specs`). Every run's effective arguments are written to the campaign manifest in
  `results/raw/*.manifest.json` together with the source-tree SHA-256.
