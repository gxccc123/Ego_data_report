"""Export an explicit public whitelist from a private benchmark audit directory.

No model outputs, raw frames, credentials, absolute paths or participant IDs are
exported. The input directory is an argument, not a developer-specific default.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("audit_root", type=Path, help="Local benchmark root")
    args = p.parse_args()
    out = Path(__file__).resolve().parents[1] / "assets/results.json"
    hashes = {}

    def read(relative):
        path = args.audit_root / relative
        content = path.read_bytes()
        hashes[path.name] = hashlib.sha256(content).hexdigest()
        return json.loads(content)

    phase = read("audit/phase2_20260921/snapshot.json")
    full = phase["full"]["analysis"]
    if not full.get("complete") or full["processed"] != 12:
        raise SystemExit("Refusing to publish a partial Phase 2 result")
    show = read("audit/expansion_20260921/show3d_scalar_paired.json")
    ego = read("audit/expansion_20260921/egoexo_common_three.json")
    broad = read("audit/expansion_20260921/five_method_analysis.json")
    snapshot = read("audit/expansion_20260921/current_snapshot.json")
    inp = read("audit/expansion_20260921/show3d_scalar_input_hash_check.json")
    eq = read("audit/expansion_20260921/hawor_ola_geometry_equivalence.json")

    def paired(src):
        keys = ["summary", "counts", "original_all_reference", "common_handframes",
                "common_joints", "reference_handframes", "reference_clips", "subject_bootstrap"]
        return {k: src[k] for k in keys if k in src}

    full_public = {k: full[k] for k in ["complete", "selected", "processed", "finite_complete", "visualized", "summary", "counts"]}
    full_public["clips"] = []
    for c in full["clips"]:
        keys = ["id", "status", "stage_times_s", "raw_stats", "raw_metrics", "full_stats", "full_metrics",
                "raw_common_stats", "full_common_stats", "observed_handframes", "observed_both_frames",
                "filled_handframes", "native_nonfinite", "world_geometry_finite"]
        row = {k: c[k] for k in keys if k in c}
        row["error"] = "Non-finite HaWoR geometry" if c["status"] != "complete" else None
        full_public["clips"].append(row)
    data = {
        "title": "Egocentric hand reconstruction benchmark — frozen research snapshot",
        "snapshot_utc": phase["snapshot_utc"],
        "disclaimer": "Local adapted subsets, not official leaderboard scores or independently verified motion capture. Output coverage is not accuracy. No claim of universal training-set disjointness.",
        "show3d": paired(show), "egoexo": paired(ego),
        "egodex_wrist_proxy": {k: broad[k] for k in ["summary", "timing", "reference_handframes", "scored_clips"]},
        "detector": {"complete": phase["detector"]["summary"]["complete"],
                     "aggregate": phase["detector"]["summary"]["aggregate"]},
        "full_hawor_show3d": full_public,
        "public_subset_counts": {k: v["counts"] for k, v in snapshot["datasets"].items()},
        "method_run_counts": {k: v["counts"] for k, v in snapshot["runs"].items()},
        "source_sha256": hashes,
        "method_commits": {
            "MINT": "1bd21e4edd6d5d2d59789ce64ee5450de24a7c2b",
            "ACE-Ego-Hand": "97578680931b3f1c8111396c100d595b98857fb8",
            "HaWoR": "66c7d4108d58a716deccd192cb7645170cdc7bd7",
            "OLA": "8470fb3 + audited dirty snapshot (not a pristine upstream release)"},
        "ola_hand_wrapper_sha256": "99d31f5098db6bce0c0b09d6e28488e8830fed2dc660df754ce32323aaa5ff1c",
        "protocol": {"units": "mm for errors; percent for coverage/PCK", "left_right": "fixed, not outcome-matched",
                     "show3d_common_joints": 20, "bootstrap_draws": 5000, "bootstrap_seed": 20260921,
                     "bootstrap_unit": "subject (retain its sampled clips together)",
                     "show3d_input": "All five branches use the same calibration-only scalar-camera resampling; SHA256 audit retained privately",
                     "world_ATE": "not evaluated; SHOW3D reference world is a moving rig",
                     "full_selection": "12 distinct reference subjects sorted by sha256(phase2-20260921:subject); first clip ID per subject; no result-based selection"},
    }
    encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    for forbidden in ["/root/", "/Users/", "ssh ", "BEGIN PRIVATE KEY", "182.242."]:
        assert forbidden not in encoded, forbidden
    out.parent.mkdir(exist_ok=True)
    out.write_text(encoded)
    print(f"Exported public aggregates: {full['finite_complete']}/12 finite, {full['visualized']} visualized")


if __name__ == "__main__":
    main()
