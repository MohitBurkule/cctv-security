"""Build configs/scenarios/showcase_all.yaml (docs/research/95): a generated perimeter_site
fenced compound, then every actor re-staged so all acts land inside 22 s.

    .venv/bin/python tools/build_showcase_all.py 19:15 configs/scenarios/showcase_all.yaml
"""
import sys

import yaml

from survsim.core.models import BehaviourSpec as B
from survsim.core.models import Camera
from cctvsec.experiments import alarm_scale as AS
from survsim.generator.spec import *

TOD = sys.argv[1] if len(sys.argv)>1 else "18:30"
spec=SceneSpec(name="showcase_all",seed=901,duration_s=22,fps=5,engine="unreal",
 site=SiteSpec(type="perimeter_site",footprint_m=(40,30),entrances=1,restricted_zones=1,blind_spots=1),
 cameras=CameraPlan(count=3,target_coverage=0.3),
 population=PopulationPlan(count=1,evasion_techniques_per_actor=1,wildlife=1),
 incidents=[IncidentPlan(type=t) for t in ["zone_intrusion","fence_climb","fence_cut","fence_tailgate","loiter","object_abandon"]])
s=AS._compose_valid(spec).scenario
P={p.id:p for p in s.population.hero}
def I(*bs): return [B(type=t,**kw) for t,kw in bs]
# hostile, staggered by approach distance
P["p000"].intent=I(("transit",{"from":[-4,-1],"to":[-4,2.5]}),("zone_intrusion",{"zone":"zone.compound","dur_s":10,"depth_m":3}))
P["p002"].intent=I(("transit",{"from":[-12,-5],"to":[-7.56,3.0]}),("fence_climb",{"segment":"fence_seg_1","climb_s":3,"dwell_s":6}))
P["p004"].intent=I(("transit",{"from":[9,-8],"to":[2.52,3.0]}),("fence_cut",{"segment":"fence_seg_3","cut_s":4,"dwell_s":5}))
P["p006"].intent=I(("transit",{"from":[5,-1],"to":[4,1]}),("fence_tailgate",{"zone":"zone.compound","wait_s":30,"dur_s":8}))
P["p008"].intent=I(("loiter",{"zone":[-10,-3],"dur_s":30,"activity":"pace","radius_m":1.5}))
P["p010"].intent=I(("transit",{"from":[14,-9],"to":[8,-4]}),("object_abandon",{"object":"backpack_large","zone":[7,-3],"leave_dist_m":6,"exit":[16,-9]}))
# twins
P["p003"].intent=I(("transit",{"from":[-13,2.5],"to":[-13,2.5]}),("patrol_guard",{"check_s":2,"zones":["zone.fence_line"]}))
P["p005"].intent=I(("transit",{"from":[13,2.5],"to":[13,2.5]}),("patrol_guard",{"check_s":2,"zones":["zone.fence_line"]}))
P["p001"].intent=I(("transit",{"from":[3,-9],"to":[1,1.5]}),("maintenance_visit",{"zone":"zone.compound","dur_s":15}))
P["p007"].intent=I(("transit",{"from":[-3,-12],"to":[-1,0]}),("maintenance_visit",{"zone":"zone.restricted_0","dur_s":15}))
P["p009"].intent=I(("commute_wait",{"zone":[-14,-8],"dur_s":30,"activity":"idle"}))
P["p011"].role="worker"; P["p011"].intent=I(("transit",{"from":[-4,-13],"to":[-3,-11]}),("staff_escort",{"target":"p007","gap_m":1.2}))
P["w000"].intent=I(("transit",{"from":[17,-2],"to":[10,-1]}),("wildlife",{"zone":"zone.yard","dur_s":20,"radius_m":8,"top_mps":2.5,"exit":[-17,-6]}))
# cameras: two fixed on the fence line from the yard + PTZ
fixed=lambda cid,x,y,yaw,tamper=[]: Camera(id=cid,type="fixed_bullet",mount={"pos":[x,y,4.5],"yaw":yaw,"pitch":-18},optics={"hfov_deg":70},capture={"res":[640,360],"fps":5},tamper=tamper)
s.cameras=[fixed("cam_01",-15,-11,45), fixed("cam_02",15,-11,135,[{"t":12.0,"kind":"cover"},{"t":18.0,"kind":"defocus"}]),
 Camera(id="cam_ptz",type="ptz",mount={"pos":[0,-13,8],"yaw":90,"pitch":-20},optics={"hfov_deg":[3.0,60]},capture={"res":[640,360],"fps":5},
  ptz={"speed_dps":60,"patrol":[{"preset":"wide","dwell_s":3.4},{"preset":"alarm","dwell_s":60}]},
  presets={"wide":{"yaw":90,"pitch":-20,"hfov_deg":60},"alarm":{"yaw":103,"pitch":-18,"hfov_deg":28}})]
s.environment.props=[p for p in s.environment.props if p.type!="camera_mount"]
d=s.model_dump(mode="json",exclude_defaults=True)
d["time_of_day"]={"start":f"2026-09-27T{TOD}:00+00:00"}
d["weather"]={"preset":"rain","rain_intensity":0.6,"wetness":0.8,"fog_density":0.1,"wind_mps":4}
d["output"]={"modalities":["rgb"],"gt":["mot","events","world_parquet","calib"]}
with open(sys.argv[2], "w") as fh:
    fh.write(yaml.safe_dump(d,sort_keys=False,width=120))
