import copy, itertools, pytest
from roomsync_ml import profile_from_answers, profile_from_survey_row, completeness, is_complete
from roomsync_ml.preprocess import ProfileError


def mk(base, dealbreakers=(), priorities=("Sleep schedule",), **kw):
    return profile_from_answers({**base, **kw}, list(dealbreakers), list(priorities))


def test_csv_rows_all_parse_and_complete(profiles):
    assert len(profiles) == 60 and all(is_complete(p) for p in profiles)
    assert all(p["origin"] == "synthetic_demo" and not p["is_real_student"] for p in profiles)


def test_validation_rejects_bad_values(base_answers):
    with pytest.raises(ProfileError): profile_from_answers({**base_answers, "tidiness": 9})
    with pytest.raises(ProfileError): profile_from_answers({**base_answers, "food": "Pizza"})
    with pytest.raises(ProfileError): profile_from_answers({"nonsense": 1})
    with pytest.raises(ProfileError): profile_from_answers(base_answers, priorities=["Sleep schedule", "Cleanliness", "Food habits", "Sharing and borrowing"])
    with pytest.raises(ProfileError): profile_from_answers(base_answers, dealbreakers=["Hates Mondays"])


def test_none_of_these_means_no_dealbreakers(base_answers):
    assert mk(base_answers, dealbreakers=["None of these"])["dealbreakers"] == []


def test_completeness_and_missing(base_answers):
    p = profile_from_answers({k: v for k, v in base_answers.items() if k != "sleep"}, [], [], strict=False)
    frac, miss = completeness(p)
    assert miss == ["priorities"] and frac < 1


def test_bounds_symmetry_determinism(engine, profiles):
    for i, j in itertools.islice(itertools.combinations(range(60), 2), 300):
        a, b = engine.pair(profiles[i], profiles[j]), engine.pair(profiles[j], profiles[i])
        assert 0 <= a.score <= 100 and abs(a.score - b.score) < 1e-9
        assert a.score == engine.pair(profiles[i], profiles[j]).score


def test_identical_profiles_score_high(engine, base_answers):
    r = engine.pair(mk(base_answers), mk(base_answers))
    assert r.score > 85 and not r.blocked


def test_scores_respond_to_answers(engine, base_answers):
    a = mk(base_answers)
    same = engine.pair(a, mk(base_answers)).score
    diff = engine.pair(a, mk(base_answers, bedtime="After 3 AM", wake="After 10 AM", tidiness=1,
                              clearing="Whenever / when someone complains")).score
    assert diff < same - 15


def test_climate_conflict(engine, base_answers):
    a, b = mk(base_answers, climate="Windows open, nothing on"), mk(base_answers, climate="AC or cooler on all night")
    d = {x["key"]: x for x in engine.pair(a, b).dimensions}["climate"]
    assert d["score"] <= 0.15 and d["verdict"] == "mismatch"


def test_dealbreaker_detected_both_directions(engine, base_answers):
    quiet = mk(base_answers, dealbreakers=["Plays music or videos on speaker"])
    loud = mk(base_answers, audio="Speakers usually")
    r1, r2 = engine.pair(quiet, loud), engine.pair(loud, quiet)
    assert r1.blocked and r2.blocked and r1.score <= 39 and r1.dealbreakers[0]["owner"] == "you" and r2.dealbreakers[0]["owner"] == "them"
    assert not engine.pair(mk(base_answers), loud).blocked


def test_nonveg_stated_constraint(engine, base_answers):
    a = mk(base_answers, nonveg_comfort="No")
    b = mk(base_answers, food="Non-vegetarian", room_eating=5)
    r = engine.pair(a, b)
    assert r.blocked and r.dealbreakers[0]["kind"] == "stated_constraint"
    assert not engine.pair(a, mk(base_answers, food="Non-vegetarian", room_eating=1)).blocked


def test_unverifiable_dealbreaker_flagged_not_blocking(engine, base_answers):
    a = mk(base_answers, dealbreakers=["Drinks alcohol in the room", "Smokes / vapes"])
    r = engine.pair(a, mk(base_answers))
    assert not r.blocked and len(r.unverified) == 2
    r2 = engine.pair(a, mk(base_answers, alcohol_in_room="Yes"))
    assert r2.blocked


def test_rank_excludes_self_duplicates_other_hostel_and_strict(engine, base_answers):
    me = mk(base_answers)
    girl = mk(base_answers, hostel="Girls hostel")
    loud = mk(base_answers, audio="Speakers usually")
    me_db = mk(base_answers, dealbreakers=["Plays music or videos on speaker"])
    cands = [("me", me), ("a", mk(base_answers)), ("a", mk(base_answers)), ("g", girl), ("l", loud)]
    ids = [r["id"] for r in engine.rank(me, cands, user_id="me")]
    assert ids.count("a") == 1 and "me" not in ids and "g" not in ids
    strict = [r["id"] for r in engine.rank(me_db, cands, strict=True)]
    assert "l" not in strict and "l" in [r["id"] for r in engine.rank(me_db, cands, strict=False)]


def test_priorities_change_weights(engine, base_answers):
    a, b = mk(base_answers, priorities=["Cleanliness"]), mk(base_answers, priorities=["Cleanliness"])
    w = engine.pair_weights(a, b); w0 = engine.pair_weights(mk(base_answers, priorities=[]), mk(base_answers, priorities=[]))
    assert w["cleanliness"] > w0["cleanliness"] and w["sleep"] == w0["sleep"]


def test_missing_data_lowers_confidence_but_works(engine, base_answers):
    partial = profile_from_answers({k: v for k, v in base_answers.items() if k not in ("food", "nonveg_comfort", "room_eating", "conflict", "sharing")}, [], ["Sleep schedule"], strict=False)
    r = engine.pair(mk(base_answers), partial)
    assert 0 < r.confidence < 1 and 0 <= r.score <= 100
    assert {d["key"]: d for d in r.dimensions}["food"]["verdict"] == "unknown"


def test_explanations_present(engine, profiles):
    r = engine.pair(profiles[0], profiles[1]).to_dict()
    assert len(r["dimensions"]) == 12 and all(d["note"] for d in r["dimensions"])


def test_latent_model_saved_and_deterministic(profiles):
    from roomsync_ml.embedding import LatentModel
    a, b = LatentModel(seed=42).fit(profiles), LatentModel(seed=42).fit(profiles)
    assert abs(a.similarity(profiles[0], profiles[1]) - b.similarity(profiles[0], profiles[1])) < 1e-9
