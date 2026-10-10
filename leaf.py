"""A teardrop leaflet cut into six straight transverse strips (SI units)."""
import numpy as np

SEGMENTS = 6
LEAF_LENGTH = .12
LEAF_SCALE = LEAF_LENGTH / .09


def bezier(points, count=18):
    p = np.array(points)
    t = np.linspace(0, 1, count, endpoint=False)[:, None]
    return (1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3]


def outline():
    upper = np.vstack([
        bezier([(0,0),(.026,.009),(.042,.031),(.061,.031)]),
        bezier([(.061,.031),(.078,.031),(.09,.018),(.09,0)]),
        [[.09,0]],
    ])
    return np.vstack([upper, upper[-2:0:-1]*[1,-1]]) * LEAF_SCALE


def clip(poly, boundary, keep_above):
    result = []
    for a,b in zip(poly, np.roll(poly,-1,axis=0)):
        inside_a = a[0] >= boundary if keep_above else a[0] <= boundary
        inside_b = b[0] >= boundary if keep_above else b[0] <= boundary
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            result.append(a+(b-a)*(boundary-a[0])/(b[0]-a[0]))
    return np.array(result)


def polygon_properties(poly):
    nxt = np.roll(poly,-1,axis=0)
    cross = poly[:,0]*nxt[:,1]-nxt[:,0]*poly[:,1]
    signed_area = cross.sum()/2
    center = ((poly+nxt)*cross[:,None]).sum(axis=0)/(6*signed_area)
    return abs(signed_area), center


def panels():
    shape = outline()
    edges = np.linspace(0, shape[:,0].max(), SEGMENTS+1)
    result = []
    for i in range(SEGMENTS):
        poly = clip(clip(shape, edges[i], True), edges[i+1], False)
        poly = poly-np.array([edges[i],0])
        area, center = polygon_properties(poly)
        result.append({'polygon':poly,'area':area,'center':center,'root':edges[i], 'length':edges[i+1]-edges[i]})
    return result
