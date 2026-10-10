"""One running C-UAS picture: scenario or live inputs → pipeline ①–⑥ → RAG card ⑦ → frame dicts.

Shared by the replay export (ops/service/export.py) and the local server (ops/service/server.py).
Keeps the latest Threat / Recommendation per track and the first alert time, so a decision ⑧ can be
logged with exactly what the operator was shown.
"""
import numpy as np

from ops.nodes.wind import estimate as wind_estimate
from ops.service.pipeline import Pipeline
from ops.sources.scenario import SIZE, generate, replay
from rag.cases.match import load as load_cases
from rag.generation.recommend import recommend
from rag.indexing.ingest import build as build_index
from rag.retrieval.query import situation

ALERT = ('HIGH', 'CRITICAL')
MARGIN = dict(drone=60.0, balloon=120.0)


def _r(x, nd=1):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def _xyz(p, nd=1):
    return [round(float(v), nd) for v in p]


def card_dict(rec):
    return dict(rec=rec.recommended_action, status=rec.action_status, why=rec.justification, enough=rec.evidence_sufficient,
                deadline=_r(rec.deadline_s), version=rec.index_version,
                cases=[dict(title=c.title, date=c.date, actions=' → '.join(c.actions_taken), outcome=c.outcome,
                            cons='; '.join(c.constraints) or '—', src=c.source, sim=c.similarity, matched=c.matched_on)
                       for c in rec.similar_cases],
                cons=[dict(kind=c.kind, text=c.text, applies=c.applies_to,
                           doc=c.citation.doc if c.citation else None, article=c.citation.article if c.citation else None,
                           quote=c.citation.quote if c.citation else None, verified=c.citation.verified if c.citation else None)
                      for c in rec.constraints])


def track_dict(tr, th, card=None):
    c = tr.classes
    out = dict(id=tr.track_id, status=tr.status, pos=_xyz(tr.pos), vel=_xyz(tr.vel, 2),
               sig=_r(np.sqrt(np.trace(np.asarray(tr.P)[:3, :3])/3)),
               probs=dict(drone=_r(c.drone, 3), balloon=_r(c.balloon, 3), bird=_r(c.bird, 3), unknown=_r(c.unknown, 3)),
               rid=tr.rid.uas_id if tr.rid else None, permitted=tr.permitted, sources=tr.sources,
               basis=tr.class_basis, check=tr.check, hist=[_xyz(h[:2]) for h in tr.history[-40:]])
    if th is not None:
        out.update(score=th.score, level=th.level, P=_r(th.p_hostile, 3), C=_r(th.consequence, 3), U=_r(th.urgency, 3),
                   tti=_r(th.tti_s), cpa=_r(th.cpa_m), zone=th.zone_id,
                   impact=_xyz(th.impact) if th.impact else None, impact_r=_r(th.impact_radius_m), fall=_r(th.fall_time_s),
                   factors=[f.value for f in th.factors], card=card)
    return out


class Session:
    def __init__(self, spacing=250.0, quality=0.95, seed=0, country='kr', dt=0.5):
        self.args = dict(spacing=spacing, quality=quality, seed=seed)
        self.sc = generate(quality=quality, seed=seed, spacing=spacing)
        self.pl = Pipeline(self.sc.cameras, self.sc.enu, self.sc.reference, ref_range_m=SIZE['drone']*self.sc.cameras[0].fx/8)
        self.index, self.cases = build_index(country), load_cases(country)
        self.zones = {z.id: z for z in self.sc.reference.zones}
        self.dt = dt
        self._frames = replay(self.sc, dt)
        self._cards = {}
        self.threats, self.recs, self.first_alert = {}, {}, {}
        self.t = 0.0

    def meta(self, bounds=None):
        sc = self.sc
        if bounds is None:
            pts = [n.pos[:2] for n in sc.nodes]+[np.array(z.center) for z in sc.reference.zones]+[tg.pos[:2] for tg in sc.targets]
            lo, hi = np.min(pts, axis=0)-200, np.max(pts, axis=0)+200
            bounds = [*_xyz(lo), *_xyz(hi)]
        return dict(source='ops pipeline · 가상 입력', scenario=sc.name, seed=self.args['seed'], quality=self.args['quality'],
                    spacing=self.args['spacing'], dt=self.dt, duration=sc.duration_s, bounds=bounds,
                    coverage_ref='0.4 m 소형 드론 기준', wind=_xyz(sc.wind, 2),
                    nodes=[dict(id=n.id, pos=_xyz(n.pos)) for n in sc.nodes],
                    zones=[dict(id=z.id, name=z.name, center=_xyz(z.center), r=z.radius, w=z.weight) for z in sc.reference.zones],
                    population=[_xyz(h, 2) for h in sc.reference.population.hotspots],
                    cameras=dict(count=len(sc.cameras), width=sc.cameras[0].width, hfov=sc.cameras[0].hfov_deg))

    def step_sim(self):
        """Advance the scenario one dt → frame dict, or None when the scenario has ended."""
        f = next(self._frames, None)
        if f is None:
            return None
        return self._step(f.t, f.node_statuses, f.camera_detections, f.rid_reports, f.wind, f.truth)

    def step_live(self, t, node_statuses, camera_detections, rid_reports, wind=None):
        """Real inputs (same contracts as the scenario) → frame dict. Wind falls back to the scenario value."""
        return self._step(t, node_statuses, camera_detections, rid_reports, wind or wind_estimate(t, self.sc.wind), [])

    def _step(self, t, statuses, dets, rids, wind, truth):
        self.t = t
        r = self.pl.step(t, statuses, dets, rids, wind)
        th = {x.track_id: x for x in r.threats}
        live = {tr.track_id: tr for tr in r.tracks}
        cards = {}
        for x in r.threats:
            self.threats[x.track_id] = x
            if x.level not in ALERT:
                continue
            self.first_alert.setdefault(x.track_id, t)
            tr = live[x.track_id]
            pop = self.sc.reference.population.density(*(x.impact or tr.pos[:2]))
            sit = situation(tr, x, self.zones.get(x.zone_id), pop)
            key = (x.track_id, x.level, sit['target_class'], sit['zone_type'], sit['population'], sit['rid'], sit['permitted'])
            if key not in self._cards:
                self._cards[key] = recommend(sit, x, self.index, self.cases)
            rec = self._cards[key].model_copy(update=dict(
                deadline_s=None if x.tti_s is None else max(0.0, x.tti_s-MARGIN.get(sit['target_class'], 60.0))))
            self.recs[x.track_id] = rec
            cards[x.track_id] = card_dict(rec)
        return dict(
            t=t,
            nodes=[dict(id=n.node_id, stability=_r(n.stability, 3), coverage=_r(n.coverage_m),
                        tilt=_r(np.degrees(np.hypot(*n.attitude[:2])))) for n in r.nodes],
            tracks=[track_dict(tr, th.get(tr.track_id), cards.get(tr.track_id)) for tr in r.tracks if tr.status != 'lost'],
            rays=[dict(node=b.node_id, az=_r(b.measurement.z[0], 4), el=_r(b.measurement.z[1], 4), label=b.label)
                  for b in r.bearing_only],
            truth=[dict(id=x['id'], cls=x['cls'], pos=_xyz(x['pos'])) for x in truth])

    def snapshot(self, track_id):
        """What the operator saw for this track: (Threat, Recommendation, first alert time)."""
        return self.threats.get(track_id), self.recs.get(track_id), self.first_alert.get(track_id)
