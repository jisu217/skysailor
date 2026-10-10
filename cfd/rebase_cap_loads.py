"""Rotate the canonical incoming-air azimuth, then shift loads to arbitrary COM.
COM coordinates are metres in the original body axes. No mass is required.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
try:
    from .cap_sweep import shift_to_com
except ImportError:
    from cap_sweep import shift_to_com


def rebase(force, torque, com, azimuth_deg=0):
    theta=np.deg2rad(azimuth_deg);c,s=np.cos(theta),np.sin(theta)
    rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]])
    f=rotation@np.asarray(force);m=rotation@np.asarray(torque)
    return f,shift_to_com(f,m,com)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('loads',type=Path);p.add_argument('--com',type=float,nargs=3,required=True,metavar=('X','Y','Z'))
    p.add_argument('--azimuth',type=float,default=0,help='Rotation about body +z from canonical incoming-air plane')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();data=json.loads(a.loads.read_text())
    with a.out.open('w') as out:
        w=csv.writer(out);w.writerow(['angle_deg','azimuth_deg','com_x_m','com_y_m','com_z_m','Fx_N','Fy_N','Fz_N','Mx_com_Nm','My_com_Nm','Mz_com_Nm','source_status'])
        for row in data['results']:
            f,m=rebase(row['force_body_N'],row['torque_origin_body_Nm'],a.com,a.azimuth)
            w.writerow([row['angle_deg'],a.azimuth,*a.com,*f,*m,row['status']])
    print(f'Wrote {a.out}; source convergence limitations are unchanged.')
