"""⑥ Threat = P(hostile) × Consequence × Urgency. See ops/docs/DESIGN.md §5.6.

All geometry is horizontal (protected zones are ground areas). Every term is returned as a
Factor so the operator sees why a target ranks where it does. Score = 100·(P·C·U)^0.7 to spread
the low end; levels LOW < 25 ≤ MEDIUM < 50 ≤ HIGH < 75 ≤ CRITICAL.
"""
import numpy as np

from ops.assessment import footprint
from ops.core.schemas import Factor, Threat

P_HOSTILE = dict(drone=.9, drone_rid=.4, drone_permitted=.05, balloon=.7, bird=.02, unknown=.5)
TAU_TTI = 600.0        # s; urgency e-folding time to a zone
TAU_FALL = 900.0       # s; urgency e-folding time to a balloon landing
FAR_DECAY = 2000.0     # m; consequence decay beyond a zone edge
VEL_SIGMA_MAX = 3.0    # m/s; above this the heading is not trusted for CPA/TTI yet


def cpa_tti(pos, vel, zone):
    """Closest point of approach (m) and time to the zone edge (s, inf if it never enters), straight line."""
    p = np.asarray(pos[:2])-np.asarray(zone.center)
    v = np.asarray(vel[:2])
    d0 = float(np.linalg.norm(p))
    if d0 <= zone.radius:
        return d0, 0.0
    v2 = float(v@v)
    if v2 < 1e-9:
        return d0, float('inf')
    tc = max(0.0, -float(p@v)/v2)
    cpa = float(np.linalg.norm(p+v*tc))
    if cpa > zone.radius:
        return cpa, float('inf')
    b, c = 2*float(p@v), d0*d0-zone.radius**2
    return cpa, max(0.0, (-b-np.sqrt(b*b-4*v2*c))/(2*v2))


def level(score):
    return 'CRITICAL' if score >= 75 else 'HIGH' if score >= 50 else 'MEDIUM' if score >= 25 else 'LOW'


def p_hostile(track):
    c = track.classes
    drone = P_HOSTILE['drone_permitted'] if track.permitted else P_HOSTILE['drone_rid'] if track.rid else P_HOSTILE['drone']
    return float(c.drone*drone+c.balloon*P_HOSTILE['balloon']+c.bird*P_HOSTILE['bird']+c.unknown*P_HOSTILE['unknown'])


def evaluate(track, wind, ref) -> Threat:
    P = p_hostile(track)
    vel_known = float(np.sqrt(np.trace(np.asarray(track.P)[3:5, 3:5])/2)) <= VEL_SIGMA_MAX
    vel = track.vel if vel_known else (0.0, 0.0, 0.0)          # new track: judge by position only
    near = [(z, *cpa_tti(track.pos, vel, z)) for z in ref.zones]
    zone, cpa, tti = min(near, key=lambda x: (x[2], x[1]), default=(None, float('inf'), float('inf')))
    pop_here = ref.population.density(*track.pos[:2])
    impact = radius = fall = None
    if track.classes.balloon > max(track.classes.drone, track.classes.bird):
        impact, radius, fall = footprint.predict(track, wind)
        pop_imp = ref.population.density(*impact)
        hit = [z for z in ref.zones if np.hypot(impact[0]-z.center[0], impact[1]-z.center[1]) < z.radius+radius]
        C = max([pop_imp]+[z.weight*.9 for z in hit])
        U = max(np.exp(-fall/TAU_FALL), np.exp(-tti/TAU_TTI) if np.isfinite(tti) else 0.0)
        c_note = f'낙하 예상 지점 인구 {pop_imp:.0%}'+(f' · {hit[0].name} 범위' if hit else '')
        u_note = f'낙하까지 {fall:.0f}초'+(f' · {zone.name} 도달 {tti:.0f}초' if np.isfinite(tti) else '')
    else:
        zc = zone.weight*(1.0 if cpa <= zone.radius else .5*np.exp(-(cpa-zone.radius)/FAR_DECAY)) if zone else 0.0
        C = max(zc, .7*pop_here)
        U = np.exp(-tti/TAU_TTI) if np.isfinite(tti) else .15*np.exp(-(cpa-(zone.radius if zone else 0))/3000)
        c_note = (f'{zone.name} 최근접 {cpa:.0f} m' if zone else '보호구역 없음')+f' · 인구 {pop_here:.0%}'
        u_note = '속도 추정 중' if not vel_known else f'{zone.name} 도달 {tti:.0f}초' if np.isfinite(tti) else '보호구역으로 접근하지 않음'
    raw = float(np.clip(P*C*U, 0, 1))
    score = round(100*raw**0.7, 1)
    top = max(('drone', 'balloon', 'bird', 'unknown'), key=lambda k: getattr(track.classes, k))
    p_note = {'drone': '드론', 'balloon': '풍선', 'bird': '조류', 'unknown': '미상'}[top]+(
        ' · 허가 비행' if track.permitted else ' · Remote ID 미허가' if track.rid else ' · Remote ID 없음')
    return Threat(track_id=track.track_id, score=score, level=level(score), p_hostile=P, consequence=float(C),
                  urgency=float(U), cpa_m=None if not np.isfinite(cpa) else float(cpa),
                  tti_s=None if not np.isfinite(tti) else float(tti), zone_id=zone.id if zone else None,
                  impact=impact, impact_radius_m=radius, fall_time_s=fall,
                  factors=[Factor(name='적대 확률', value=p_note, contribution=P),
                           Factor(name='피해 규모', value=c_note, contribution=float(C)),
                           Factor(name='긴급도', value=u_note, contribution=float(U))])
