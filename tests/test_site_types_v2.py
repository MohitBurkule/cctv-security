"""Infinite sites v2: all 14 site types generate, validate and lay out, 3 seeds each."""
import pytest
import yaml

from survsim.core.loader import load_scenario
from cctvsec.experiments.alarm_scale import _compose_valid
from survsim.generator.batch import ALL_SITE_TYPES, SITE_PROFILES, SITE_TYPES_V2
from survsim.generator.layout import SITE_TYPES, build_layout
from survsim.generator.spec import (
    CameraPlan,
    IncidentPlan,
    PopulationPlan,
    SceneSpec,
    SiteSpec,
    SiteType,
)

VARIANT_KEY = {"loading_dock": "dock", "school_gate": "school", "rail_platform": "platform",
               "hospital_entrance": "hospital", "utility_yard": "utility",
               "construction_site": "stage", "farm_yard": "farm", "residential_close": "street"}


def test_fourteen_types_everywhere():
    assert len(ALL_SITE_TYPES) == 14 == len(set(ALL_SITE_TYPES))
    assert set(SiteType.__args__) == set(ALL_SITE_TYPES) == set(SITE_TYPES)  # type: ignore[attr-defined]
    assert set(SITE_PROFILES) == set(SITE_TYPES_V2)


@pytest.mark.parametrize("site", ALL_SITE_TYPES)
def test_every_type_generates_and_validates(site, tmp_path):
    for seed in (11, 12, 13):
        inc = [IncidentPlan(type=SITE_PROFILES[site]["incident"])] if site in SITE_PROFILES else []
        spec = SceneSpec(name=f"v2_{site}_{seed}", seed=seed, duration_s=20,
                         site=SiteSpec(type=site, footprint_m=(40, 30)),
                         cameras=CameraPlan(count=3, target_coverage=0.3, resolution=(640, 360)),
                         population=PopulationPlan(count=6, evasion_techniques_per_actor=0),
                         incidents=inc)
        scene = _compose_valid(spec)
        assert scene.valid, (site, seed, scene.issues)
        if inc:
            assert any(a.person.hard_negative_for for a in scene.arcs), (site, seed)
        y = tmp_path / f"{site}_{seed}.yaml"
        y.write_text(yaml.safe_dump(scene.scenario.model_dump(mode="json", exclude_defaults=True)))
        s = load_scenario(y)                      # what `survsim validate` does
        assert s.cameras and s.population.hero
        L = build_layout(site, seed)
        assert L.report["ok"], (site, seed, L.report["failures"])


def test_v2_layouts_deterministic_and_variant_bearing():
    for site in SITE_TYPES_V2:
        a, b = build_layout(site, 4), build_layout(site, 4)
        assert a.to_dict() == b.to_dict()
        key = VARIANT_KEY[site]
        variants = {build_layout(site, k).variant[key] for k in range(1, 10)}
        assert len(variants) >= 2, (site, variants)
