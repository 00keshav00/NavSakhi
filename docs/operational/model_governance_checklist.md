# SafeShe Model Governance Checklist

This document governs how the SafeShe ML Safety Model is updated when new safety datasets are acquired. The model must never be silently altered in production.

## 1. Feature Evaluation (Pre-Training)
Before feeding a newly accepted safety dataset (e.g., aggregated police incidents) into the model:
- [ ] **Data Quality Review**: Verify missingness, spatial resolution, and temporal resolution meet thresholds.
- [ ] **Distribution Shift Analysis**: Compare the new feature distributions (mean, median, variance) against the existing model's baseline distributions.
- [ ] **Privacy Audit**: Final confirmation that no raw PII or sensitive victim data leaked into the aggregated features.

## 2. Versioning
- [ ] **Dataset Versioning**: Lock the `training_dataset_version`.
- [ ] **Feature Pipeline Versioning**: Assign a `feature_pipeline_version` if transformation logic changed.
- [ ] **Model Versioning**: Increment the `model_version` (e.g., `safeshe-safety-v1.1`).

## 3. Offline Evaluation
- [ ] **Calibration**: Verify the model's confidence scores accurately reflect prediction probabilities.
- [ ] **Ranking Consistency**: Ensure that objectively safer routes continue to outrank dangerous routes.
- [ ] **Discrimination**: Verify the model actively differentiates between high-exposure (night walking) and low-exposure (mid-day metro) segments.
- [ ] **False Positives/Negatives**: Monitor the rate of extreme scores (e.g., scoring a notoriously unsafe area as perfectly safe).

## 4. Regression & Deployment
- [ ] **Safety Regressions**: Ensure `REC-01` through `REC-15` pass with the new model weights.
- [ ] **Reviewer Benchmark**: Human trust-review panel confirms the explanations and trade-offs remain physically logical.
- [ ] **Approval & Release**: Explicit sign-off required to promote `model_version` to production.
