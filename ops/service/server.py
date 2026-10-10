"""Local ops server: runs the C-UAS picture continuously and serves the screen.

python -m ops.service.server [--port 8090] [--host 127.0.0.1] [--speed 2] [--spacing 250 --quality 0.95 --seed 0]
→ open http://localhost:8090/

- sim mode   (default) steps the virtual scenario in real time × speed and loops it
- live mode  steps every dt on whatever arrived at POST /api/ops/ingest (node status, camera detections,
             decoded Remote ID) or POST /api/ops/ingest/remote-id (raw Remote ID frames from the dome MCU,
             decoded here) — the entry points for real devices in phase 4
Frames go to the screen over WS /api/ops/ws. Decisions (POST /api/ops/decision) are written to
outputs/ops/decisions.jsonl together with the threat and card the server last showed for that track.
Separate from the existing dashboard (dashboard.py); nothing there is touched.
"""
import argparse
import asyncio
import contextlib
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ops.service.api as api
from ops.core.schemas import CameraDetection, NodeStatus, RemoteID, WindEstimate
from ops.service.session import Session
from ops.sources.remote_id import Assembler, RawRemoteID

PROTOTYPES = Path(__file__).resolve().parents[2]/'prototypes'


class Control(BaseModel):
    action: Literal['pause', 'resume', 'restart', 'speed', 'mode']
    value: float | str | None = None


class RidReport(BaseModel):
    node_id: str
    rid: RemoteID


class Ingest(BaseModel):
    t: float | None = None
    node_statuses: list[NodeStatus] = Field(default_factory=list)
    camera_detections: list[CameraDetection] = Field(default_factory=list)
    rid_reports: list[RidReport] = Field(default_factory=list)
    wind: WindEstimate | None = None


class Runner:
    def __init__(self, speed=2.0, **session_args):
        self.session_args = session_args
        self.speed, self.paused, self.mode = speed, False, 'sim'
        self.subscribers: set[asyncio.Queue] = set()
        self.latest = None
        self.buffer = Ingest()
        self.new_session()

    def new_session(self):
        self.session = Session(**self.session_args)
        self.rid_assembler = Assembler()
        self.latest = None
        self.live_t = 0.0
        api.snapshot_provider = self.session.snapshot

    async def publish(self, msg):
        for q in list(self.subscribers):
            if q.qsize() < 20:                       # slow client: drop frames rather than block
                q.put_nowait(msg)

    def status(self):
        return dict(mode=self.mode, paused=self.paused, speed=self.speed, t=self.session.t, clients=len(self.subscribers))

    async def loop(self):
        while True:
            dt = self.session.dt
            if not self.paused:
                if self.mode == 'sim':
                    frame = await asyncio.to_thread(self.session.step_sim)
                    if frame is None:
                        await asyncio.to_thread(self.new_session)
                        await self.publish(dict(type='meta', meta=self.session.meta(), status=self.status()))
                        continue
                else:
                    b, self.buffer = self.buffer, Ingest()
                    self.live_t = b.t if b.t is not None else self.live_t+dt
                    frame = await asyncio.to_thread(self.session.step_live, self.live_t, b.node_statuses, b.camera_detections,
                                                    [(r.node_id, r.rid) for r in b.rid_reports], b.wind)
                self.latest = frame
                await self.publish(dict(type='frame', frame=frame))
            await asyncio.sleep(dt/(self.speed if self.mode == 'sim' else 1.0))


def create_app(speed=2.0, **session_args) -> FastAPI:
    runner = Runner(speed, **session_args)

    @contextlib.asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(runner.loop())
        yield
        task.cancel()

    app = FastAPI(title='Skysailor ops (local)', lifespan=lifespan)
    app.state.runner = runner
    app.include_router(api.router)

    @app.get('/api/ops/meta')
    def meta():
        return runner.session.meta()

    @app.get('/api/ops/state')
    def state():
        return dict(status=runner.status(), frame=runner.latest)

    @app.post('/api/ops/control')
    async def control(c: Control):
        if c.action == 'pause':
            runner.paused = True
        elif c.action == 'resume':
            runner.paused = False
        elif c.action == 'speed' and c.value:
            runner.speed = max(0.1, min(20.0, float(c.value)))
        elif c.action == 'mode' and c.value in ('sim', 'live'):
            runner.mode = c.value
            await asyncio.to_thread(runner.new_session)
        elif c.action == 'restart':
            await asyncio.to_thread(runner.new_session)
        if c.action in ('restart', 'mode'):
            await runner.publish(dict(type='meta', meta=runner.session.meta(), status=runner.status()))
        return runner.status()

    @app.post('/api/ops/ingest', status_code=202)
    def ingest(body: Ingest):
        """Device inputs for live mode; accumulated until the next step."""
        b = runner.buffer
        b.node_statuses += body.node_statuses
        b.camera_detections += body.camera_detections
        b.rid_reports += body.rid_reports
        b.wind = body.wind or b.wind
        b.t = body.t if body.t is not None else b.t
        return dict(mode=runner.mode, queued=dict(nodes=len(b.node_statuses), detections=len(b.camera_detections), rid=len(b.rid_reports)))

    @app.post('/api/ops/ingest/remote-id', status_code=202)
    def ingest_remote_id(frames: list[RawRemoteID]):
        """Raw Remote ID frames forwarded by the dome MCU; decoded and joined per sender here."""
        decoded, errors = [], []
        for f in frames:
            try:
                out = runner.rid_assembler.add(f)
            except ValueError as e:
                errors.append(dict(mac=f.mac, error=str(e)))
                continue
            if out is not None:
                runner.buffer.rid_reports.append(RidReport(node_id=out[0], rid=out[1]))
                decoded.append(out[1].uas_id)
        return dict(mode=runner.mode, accepted=len(frames), aircraft=decoded, errors=errors)

    @app.websocket('/api/ops/ws')
    async def ws(sock: WebSocket):
        await sock.accept()
        q: asyncio.Queue = asyncio.Queue()
        runner.subscribers.add(q)
        try:
            await sock.send_json(dict(type='meta', meta=runner.session.meta(), status=runner.status()))
            while True:
                await sock.send_json(await q.get())
        except WebSocketDisconnect:
            pass
        finally:
            runner.subscribers.discard(q)

    @app.get('/')
    def index():
        return RedirectResponse('/c-uas-ops.html')

    app.mount('/', StaticFiles(directory=PROTOTYPES, html=True), name='prototypes')
    return app


def main():
    ap = argparse.ArgumentParser(description='Skysailor local ops server')
    ap.add_argument('--host', default='127.0.0.1', help='0.0.0.0 to let others on the network connect')
    ap.add_argument('--port', type=int, default=8090)
    ap.add_argument('--speed', type=float, default=2.0)
    ap.add_argument('--spacing', type=float, default=250.0)
    ap.add_argument('--quality', type=float, default=0.95)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    import uvicorn
    uvicorn.run(create_app(a.speed, spacing=a.spacing, quality=a.quality, seed=a.seed), host=a.host, port=a.port)


if __name__ == '__main__':
    main()
