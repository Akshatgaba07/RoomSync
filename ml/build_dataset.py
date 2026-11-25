"""Reproducible dataset preparation: raw survey CSV -> canonical, provenance-labelled profiles.

Original CSV is never modified. Outputs (datasets/processed/):
  profiles.json          canonical profiles + provenance fields
  profiles_encoded.csv   numeric feature matrix (NaN preserved) with record_id
  data_report.json       schema / missing-value / distribution report
Run: python ml/build_dataset.py
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd
from paths import RAW, PROCESSED
from roomsync_ml import schema as S
from roomsync_ml.preprocess import profile_from_survey_row, raw_feature_vector, feature_names, completeness


def main():
    df = pd.read_csv(RAW)
    expected = {q["col"] for q in S.QUESTIONS.values() if q["col"]} | {S.DEALBREAKER_COL, S.PRIORITY_COL}
    missing_cols = expected - set(df.columns)
    assert not missing_cols, f"CSV is missing columns: {missing_cols}"
    synth = df[S.SYNTHETIC_COL].astype(str)
    profiles = []
    for i, row in df.iterrows():
        p = profile_from_survey_row(row)
        frac, miss = completeness(p)
        p.update(record_id=f"SYN-{i+1:03d}", source="demo_responses_SYNTHETIC.csv", row_index=int(i),
                 origin="synthetic_demo", is_real_student=False, synthetic_flag=synth.iloc[i],
                 completeness=frac)
        profiles.append(p)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "profiles.json").write_text(json.dumps(profiles, indent=1))
    X = np.vstack([raw_feature_vector(p) for p in profiles])
    enc = pd.DataFrame(X, columns=feature_names())
    enc.insert(0, "record_id", [p["record_id"] for p in profiles])
    enc.to_csv(PROCESSED / "profiles_encoded.csv", index=False)
    report = {
        "n_rows": len(df), "n_columns": df.shape[1],
        "synthetic_column_values": synth.value_counts().to_dict(),
        "n_real_students_in_file": int((~synth.str.contains("SYNTHETIC")).sum()),
        "note": "The SYNTHETIC column is constant: every row is synthetic. The ~10 real Bennett responses are NOT in this file.",
        "hostel_counts": df[S.QUESTIONS["hostel"]["col"]].value_counts().to_dict(),
        "null_counts": {c: int(v) for c, v in df.isna().sum().items() if v},
        "label_column": {"name": S.CURRENT_COMPAT_COL, "non_null": int(df[S.CURRENT_COMPAT_COL].notna().sum()),
                         "consequence": "No supervised compatibility labels exist."},
        "mean_completeness": float(np.mean([p["completeness"] for p in profiles])),
        "dealbreaker_frequency": pd.Series([d for p in profiles for d in p["dealbreakers"]]).value_counts().to_dict(),
        "none_of_these_count": int(sum(1 for p in profiles if not p["dealbreakers"])),
        "priority_frequency": pd.Series([d for p in profiles for d in p["priorities"]]).value_counts().to_dict(),
    }
    (PROCESSED / "data_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))

if __name__ == "__main__":
    main()
