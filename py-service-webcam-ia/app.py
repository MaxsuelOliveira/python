import argparse
import asyncio
import base64
import json
import logging
import smtplib
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from ultralytics import YOLO
import uvicorn

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
SNAPSHOT_DIR = APP_DIR / "snapshots"
RULES_FILE = DATA_DIR / "rules.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
DB_FILE = DATA_DIR / "events.db"
DEFAULT_MODEL = "yolov8n.pt"
LOGGER = logging.getLogger("env-monitor")

COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
    "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed",
    "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven",
    "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

DEFAULT_SETTINGS = {
    "camera": {
        "source": "0",
        "width": 1280,
        "height": 720,
        "fps_limit": 8,
        "preview_jpeg_quality": 70,
    },
    "model": {
        "path": DEFAULT_MODEL,
        "confidence": 0.45,
        "iou": 0.45,
        "classes": ["person", "dog", "cat", "couch", "chair", "bed", "bird"],
        "skip_frames": 1,
    },
    "alerts": {
        "cooldown_seconds": 20,
        "snapshot_dir": str(SNAPSHOT_DIR),
    },
}

DEFAULT_RULES = {
    "zones": [
        {
            "id": "sofa_area",
            "name": "Sofá",
            "shape": "rect",
            "x": 0.45,
            "y": 0.45,
            "w": 0.45,
            "h": 0.40,
            "color": "#22c55e"
        },
        {
            "id": "room_area",
            "name": "Quarto / Ambiente",
            "shape": "rect",
            "x": 0.05,
            "y": 0.08,
            "w": 0.90,
            "h": 0.84,
            "color": "#3b82f6"
        }
    ],
    "rules": [
        {
            "id": "dog_on_sofa",
            "name": "Cachorro no sofá",
            "enabled": True,
            "cooldown_seconds": 30,
            "condition": {
                "type": "object_in_zone",
                "object": "dog",
                "zone_id": "sofa_area",
                "min_confidence": 0.40,
                "min_overlap": 0.15,
                "for_frames": 5
            },
            "actions": [
                {"type": "websocket"},
                {"type": "snapshot"},
                {"type": "webhook", "enabled": False, "url": "https://example.com/webhook"},
                {"type": "slack", "enabled": False, "webhook_url": "https://hooks.slack.com/services/..."},
                {"type": "telegram", "enabled": False, "bot_token": "", "chat_id": ""},
                {"type": "email", "enabled": False, "smtp_host": "smtp.gmail.com", "smtp_port": 587, "username": "", "password": "", "from_email": "", "to": [""]}
            ]
        },
        {
            "id": "room_without_person",
            "name": "Quarto sem ninguém",
            "enabled": False,
            "cooldown_seconds": 60,
            "condition": {
                "type": "object_absent",
                "object": "person",
                "zone_id": "room_area",
                "min_confidence": 0.35,
                "for_seconds": 20
            },
            "actions": [
                {"type": "websocket"},
                {"type": "snapshot"}
            ]
        }
    ]
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso() -> str:
    return utc_now().isoformat()


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    if not RULES_FILE.exists():
        RULES_FILE.write_text(json.dumps(DEFAULT_RULES, indent=2, ensure_ascii=False), encoding="utf-8")
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def clamp(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))


def norm_zone_to_pixels(zone: Dict[str, Any], width: int, height: int) -> Tuple[int, int, int, int]:
    x = int(clamp(zone["x"], 0.0, 1.0) * width)
    y = int(clamp(zone["y"], 0.0, 1.0) * height)
    w = int(clamp(zone["w"], 0.0, 1.0) * width)
    h = int(clamp(zone["h"], 0.0, 1.0) * height)
    return x, y, max(w, 1), max(h, 1)


def bbox_iou(a: List[float], b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    iw = max(0.0, x2 - x1)
    ih = max(0.0, y2 - y1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def overlap_with_zone(bbox: List[float], zone_box: Tuple[int, int, int, int]) -> float:
    zx, zy, zw, zh = zone_box
    zone_bbox = [zx, zy, zx + zw, zy + zh]
    return bbox_iou(bbox, zone_bbox)


def jpg_base64(frame: np.ndarray, quality: int = 70) -> str:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


class SettingsModel(BaseModel):
    camera: Dict[str, Any]
    model: Dict[str, Any]
    alerts: Dict[str, Any]


class RulesPayload(BaseModel):
    zones: List[Dict[str, Any]] = Field(default_factory=list)
    rules: List[Dict[str, Any]] = Field(default_factory=list)


class AppState(BaseModel):
    running: bool = False
    latest_frame_ts: Optional[str] = None
    latest_preview_b64: Optional[str] = None
    fps: float = 0.0
    model_name: str = DEFAULT_MODEL
    source: str = "0"
    detections: List[Dict[str, Any]] = Field(default_factory=list)
    active_rules: int = 0
    recent_event_ids: List[str] = Field(default_factory=list)


class DetectionEngine:
    def __init__(self, model_path: str, confidence: float = 0.45, iou: float = 0.45, classes: Optional[List[str]] = None):
        self.model_path = model_path
        self.confidence = confidence
        self.iou = iou
        self.model = YOLO(model_path)
        self.class_filter = set(classes or [])

    def update(self, model_path: str, confidence: float, iou: float, classes: List[str]) -> None:
        if model_path != self.model_path:
            self.model_path = model_path
            self.model = YOLO(model_path)
        self.confidence = confidence
        self.iou = iou
        self.class_filter = set(classes or [])

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        results = self.model.predict(source=frame, conf=self.confidence, iou=self.iou, verbose=False)
        detections: List[Dict[str, Any]] = []
        if not results:
            return detections
        result = results[0]
        names = result.names
        boxes = result.boxes
        if boxes is None:
            return detections
        for box in boxes:
            cls_id = int(box.cls[0].item())
            label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else names[cls_id]
            if self.class_filter and label not in self.class_filter:
                continue
            conf = float(box.conf[0].item())
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            detections.append({
                "class": label,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2]
            })
        return detections


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    camera_source TEXT,
                    confidence REAL,
                    payload_json TEXT NOT NULL,
                    snapshot_path TEXT
                )
                """
            )
            conn.commit()

    def insert_event(self, event: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (id, timestamp, rule_id, rule_name, event_type, camera_source, confidence, payload_json, snapshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"], event["timestamp"], event["rule_id"], event["rule_name"], event["event_type"],
                    event.get("camera_source"), event.get("confidence"), json.dumps(event, ensure_ascii=False), event.get("snapshot_path")
                )
            )
            conn.commit()

    def list_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]


class ConnectionManager:
    def __init__(self):
        self._clients: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._clients.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self._clients:
                self._clients.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        async with self._lock:
            clients = list(self._clients)
        dead = []
        for client in clients:
            try:
                await client.send_json(message)
            except Exception:
                dead.append(client)
        if dead:
            async with self._lock:
                for client in dead:
                    if client in self._clients:
                        self._clients.remove(client)


@dataclass
class RuleRuntimeState:
    consecutive_matches: int = 0
    last_seen_ts: float = 0.0
    last_fired_ts: float = 0.0
    last_absent_start_ts: float = 0.0


class RuleEngine:
    def __init__(self):
        self.runtime: Dict[str, RuleRuntimeState] = defaultdict(RuleRuntimeState)

    def evaluate(
        self,
        rules_payload: Dict[str, Any],
        detections: List[Dict[str, Any]],
        frame_shape: Tuple[int, int, int],
        now_ts: float,
    ) -> List[Dict[str, Any]]:
        zones = {z["id"]: z for z in rules_payload.get("zones", [])}
        events: List[Dict[str, Any]] = []
        height, width = frame_shape[:2]

        for rule in rules_payload.get("rules", []):
            if not rule.get("enabled", True):
                continue
            rule_id = rule["id"]
            state = self.runtime[rule_id]
            condition = rule.get("condition", {})
            ctype = condition.get("type")
            cooldown = float(rule.get("cooldown_seconds", 20))
            if now_ts - state.last_fired_ts < cooldown:
                if ctype != "object_absent":
                    state.consecutive_matches = 0
                continue

            if ctype == "object_present":
                event = self._eval_object_present(rule, detections, state, now_ts)
            elif ctype == "object_in_zone":
                event = self._eval_object_in_zone(rule, detections, zones, width, height, state, now_ts)
            elif ctype == "object_absent":
                event = self._eval_object_absent(rule, detections, zones, width, height, state, now_ts)
            elif ctype == "overlap":
                event = self._eval_overlap(rule, detections, zones, width, height, state, now_ts)
            else:
                event = None

            if event:
                state.last_fired_ts = now_ts
                events.append(event)

        return events

    def _filter_object(self, detections, obj_name: str, min_conf: float):
        return [d for d in detections if d["class"] == obj_name and d["confidence"] >= min_conf]

    def _base_event(self, rule: Dict[str, Any], confidence: Optional[float], extra: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "timestamp": utc_iso(),
            "event_type": rule.get("condition", {}).get("type", "rule_triggered"),
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "confidence": confidence,
            "actions": rule.get("actions", []),
            **extra,
        }

    def _eval_object_present(self, rule, detections, state, now_ts):
        cond = rule["condition"]
        objs = self._filter_object(detections, cond["object"], float(cond.get("min_confidence", 0.3)))
        if objs:
            state.consecutive_matches += 1
            if state.consecutive_matches >= int(cond.get("for_frames", 1)):
                best = max(objs, key=lambda x: x["confidence"])
                state.consecutive_matches = 0
                return self._base_event(rule, best["confidence"], {"detections": objs})
        else:
            state.consecutive_matches = 0
        return None

    def _eval_object_in_zone(self, rule, detections, zones, width, height, state, now_ts):
        cond = rule["condition"]
        zone = zones.get(cond["zone_id"])
        if not zone:
            return None
        zone_box = norm_zone_to_pixels(zone, width, height)
        min_overlap = float(cond.get("min_overlap", 0.1))
        objs = self._filter_object(detections, cond["object"], float(cond.get("min_confidence", 0.3)))
        matched = []
        for det in objs:
            ov = overlap_with_zone(det["bbox"], zone_box)
            if ov >= min_overlap:
                matched.append({**det, "overlap": ov})
        if matched:
            state.consecutive_matches += 1
            if state.consecutive_matches >= int(cond.get("for_frames", 1)):
                best = max(matched, key=lambda x: x["confidence"])
                state.consecutive_matches = 0
                return self._base_event(rule, best["confidence"], {"detections": matched, "zone": zone})
        else:
            state.consecutive_matches = 0
        return None

    def _eval_object_absent(self, rule, detections, zones, width, height, state, now_ts):
        cond = rule["condition"]
        zone = zones.get(cond.get("zone_id")) if cond.get("zone_id") else None
        objs = self._filter_object(detections, cond["object"], float(cond.get("min_confidence", 0.3)))
        if zone:
            zone_box = norm_zone_to_pixels(zone, width, height)
            objs = [d for d in objs if overlap_with_zone(d["bbox"], zone_box) > 0.05]
        if not objs:
            if state.last_absent_start_ts <= 0:
                state.last_absent_start_ts = now_ts
            if now_ts - state.last_absent_start_ts >= float(cond.get("for_seconds", 5)):
                state.last_absent_start_ts = now_ts
                return self._base_event(rule, None, {"detections": [], "zone": zone})
        else:
            state.last_absent_start_ts = 0.0
        return None

    def _eval_overlap(self, rule, detections, zones, width, height, state, now_ts):
        cond = rule["condition"]
        object_a = self._filter_object(detections, cond["object_a"], float(cond.get("min_confidence_a", 0.3)))
        min_iou = float(cond.get("min_iou", 0.1))
        matched = []
        if cond.get("zone_b"):
            zone = zones.get(cond["zone_b"])
            if not zone:
                return None
            zone_box = norm_zone_to_pixels(zone, width, height)
            for det in object_a:
                iou = overlap_with_zone(det["bbox"], zone_box)
                if iou >= min_iou:
                    matched.append({**det, "overlap": iou})
        else:
            object_b = self._filter_object(detections, cond["object_b"], float(cond.get("min_confidence_b", 0.3)))
            for da in object_a:
                for db in object_b:
                    iou = bbox_iou(da["bbox"], db["bbox"])
                    if iou >= min_iou:
                        matched.append({"a": da, "b": db, "overlap": iou})
        if matched:
            state.consecutive_matches += 1
            if state.consecutive_matches >= int(cond.get("for_frames", 1)):
                state.consecutive_matches = 0
                conf = matched[0].get("confidence") or matched[0].get("a", {}).get("confidence")
                return self._base_event(rule, conf, {"detections": matched})
        else:
            state.consecutive_matches = 0
        return None


class ActionDispatcher:
    def __init__(self, db: Database, manager: ConnectionManager, state: AppState):
        self.db = db
        self.manager = manager
        self.state = state

    async def dispatch(self, event: Dict[str, Any], frame: np.ndarray, settings: Dict[str, Any]) -> Dict[str, Any]:
        actions = event.pop("actions", [])
        event["camera_source"] = self.state.source
        for action in actions:
            action_type = action.get("type")
            if action_type == "snapshot":
                event["snapshot_path"] = self._save_snapshot(event, frame)
            elif action_type == "websocket":
                pass

        self.db.insert_event(event)
        self.state.recent_event_ids = [event["id"], *self.state.recent_event_ids[:19]]
        await self.manager.broadcast({"type": "event", "payload": event})
        await self._dispatch_integrations(event, actions)
        return event

    def _save_snapshot(self, event: Dict[str, Any], frame: np.ndarray) -> str:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{event['id']}.jpg"
        path = SNAPSHOT_DIR / filename
        cv2.imwrite(str(path), frame)
        return filename

    async def _dispatch_integrations(self, event: Dict[str, Any], actions: List[Dict[str, Any]]):
        tasks = []
        for action in actions:
            if action.get("enabled") is False:
                continue
            action_type = action.get("type")
            if action_type == "webhook":
                url = action.get("url")
                if url:
                    tasks.append(self._send_webhook(url, event))
            elif action_type == "slack":
                hook = action.get("webhook_url")
                if hook:
                    tasks.append(self._send_slack(hook, event))
            elif action_type == "telegram":
                token = action.get("bot_token")
                chat_id = action.get("chat_id")
                if token and chat_id:
                    tasks.append(self._send_telegram(token, chat_id, event))
            elif action_type == "email":
                tasks.append(asyncio.to_thread(self._send_email, action, event))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_webhook(self, url: str, event: Dict[str, Any]):
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=event)

    async def _send_slack(self, webhook_url: str, event: Dict[str, Any]):
        text = f"🚨 Regra acionada: {event['rule_name']}\nHorário: {event['timestamp']}\nConfiança: {event.get('confidence')}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(webhook_url, json={"text": text})

    async def _send_telegram(self, token: str, chat_id: str, event: Dict[str, Any]):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        text = f"Regra acionada: {event['rule_name']}\nHorário: {event['timestamp']}\nConfiança: {event.get('confidence')}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text})

    def _send_email(self, cfg: Dict[str, Any], event: Dict[str, Any]):
        to_list = [x for x in cfg.get("to", []) if x]
        if not to_list:
            return
        msg = EmailMessage()
        msg["Subject"] = f"[Env Monitor] {event['rule_name']}"
        msg["From"] = cfg.get("from_email") or cfg.get("username")
        msg["To"] = ", ".join(to_list)
        msg.set_content(json.dumps(event, indent=2, ensure_ascii=False))
        host = cfg.get("smtp_host")
        port = int(cfg.get("smtp_port", 587))
        username = cfg.get("username")
        password = cfg.get("password")
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)


class MonitorService:
    def __init__(self, state: AppState, manager: ConnectionManager, db: Database):
        self.state = state
        self.manager = manager
        self.db = db
        self.rule_engine = RuleEngine()
        self.dispatcher = ActionDispatcher(db, manager, state)
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.capture: Optional[cv2.VideoCapture] = None
        self.last_frame: Optional[np.ndarray] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self, loop: asyncio.AbstractEventLoop):
        if self.thread and self.thread.is_alive():
            return
        self.loop = loop
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.capture is not None:
            self.capture.release()
        self.state.running = False

    def _source_value(self, raw: str):
        try:
            return int(raw)
        except Exception:
            return raw

    def _draw(self, frame: np.ndarray, detections: List[Dict[str, Any]], rules_payload: Dict[str, Any]) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]
        for zone in rules_payload.get("zones", []):
            x, y, zw, zh = norm_zone_to_pixels(zone, w, h)
            color = (60, 180, 75)
            cv2.rectangle(out, (x, y), (x + zw, y + zh), color, 2)
            cv2.putText(out, zone["name"], (x, max(20, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 140, 255), 2)
            label = f"{det['class']} {det['confidence']:.2f}"
            cv2.putText(out, label, (x1, max(20, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 140, 255), 2)
        return out

    def _run(self):
        rules_payload = load_json(RULES_FILE, DEFAULT_RULES)
        settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        model_cfg = settings["model"]
        engine = DetectionEngine(
            model_cfg.get("path", DEFAULT_MODEL),
            float(model_cfg.get("confidence", 0.45)),
            float(model_cfg.get("iou", 0.45)),
            list(model_cfg.get("classes", [])),
        )
        camera_cfg = settings["camera"]
        source = str(camera_cfg.get("source", "0"))
        self.state.source = source
        self.state.model_name = model_cfg.get("path", DEFAULT_MODEL)
        self.capture = cv2.VideoCapture(self._source_value(source))
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(camera_cfg.get("width", 1280)))
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(camera_cfg.get("height", 720)))
        skip_frames = int(model_cfg.get("skip_frames", 1))
        fps_limit = max(1, int(camera_cfg.get("fps_limit", 8)))
        delay = 1.0 / fps_limit
        frame_count = 0
        self.state.running = True
        last_perf = time.perf_counter()

        while not self.stop_event.is_set():
            ok, frame = self.capture.read()
            if not ok or frame is None:
                time.sleep(0.2)
                continue

            frame_count += 1
            self.last_frame = frame.copy()
            current_settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
            current_rules = load_json(RULES_FILE, DEFAULT_RULES)
            if current_settings != settings:
                settings = current_settings
                model_cfg = settings["model"]
                engine.update(
                    model_cfg.get("path", DEFAULT_MODEL),
                    float(model_cfg.get("confidence", 0.45)),
                    float(model_cfg.get("iou", 0.45)),
                    list(model_cfg.get("classes", [])),
                )
                camera_cfg = settings["camera"]
                skip_frames = int(model_cfg.get("skip_frames", 1))
                fps_limit = max(1, int(camera_cfg.get("fps_limit", 8)))
                delay = 1.0 / fps_limit
                self.state.model_name = model_cfg.get("path", DEFAULT_MODEL)
            rules_payload = current_rules

            if skip_frames > 1 and frame_count % skip_frames != 0:
                time.sleep(delay)
                continue

            detections = engine.detect(frame)
            preview = self._draw(frame, detections, rules_payload)
            now = time.perf_counter()
            dt = now - last_perf
            if dt > 0:
                self.state.fps = 1.0 / dt
            last_perf = now
            self.state.detections = detections
            self.state.active_rules = sum(1 for r in rules_payload.get("rules", []) if r.get("enabled", True))
            self.state.latest_frame_ts = utc_iso()
            self.state.latest_preview_b64 = jpg_base64(preview, int(camera_cfg.get("preview_jpeg_quality", 70)))

            events = self.rule_engine.evaluate(rules_payload, detections, frame.shape, time.time())
            for event in events:
                future = asyncio.run_coroutine_threadsafe(self.dispatcher.dispatch(event, preview, settings), self.loop)
                try:
                    future.result(timeout=0.1)
                except Exception:
                    pass

            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.manager.broadcast({
                        "type": "state",
                        "payload": self.state.model_dump(),
                    }),
                    self.loop,
                )
            time.sleep(delay)

        if self.capture is not None:
            self.capture.release()
        self.state.running = False


ensure_dirs()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title="Environment Monitor API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state = AppState()
manager = ConnectionManager()
db = Database(DB_FILE)
monitor = MonitorService(state, manager, db)


@app.on_event("startup")
async def on_startup():
    ensure_dirs()
    loop = asyncio.get_running_loop()
    monitor.start(loop)


@app.on_event("shutdown")
async def on_shutdown():
    monitor.stop()


@app.get("/health")
def health():
    return {"status": "ok", "running": state.running, "time": utc_iso()}


@app.get("/api/state")
def get_state():
    return state


@app.get("/api/settings")
def get_settings():
    return load_json(SETTINGS_FILE, DEFAULT_SETTINGS)


@app.put("/api/settings")
def put_settings(payload: SettingsModel):
    save_json(SETTINGS_FILE, payload.model_dump())
    return {"ok": True}


@app.get("/api/rules")
def get_rules():
    return load_json(RULES_FILE, DEFAULT_RULES)


@app.put("/api/rules")
def put_rules(payload: RulesPayload):
    save_json(RULES_FILE, payload.model_dump())
    return {"ok": True}


@app.get("/api/events")
def get_events(limit: int = 100):
    return db.list_events(limit=min(max(limit, 1), 500))


@app.get("/api/snapshots/{filename}")
def get_snapshot(filename: str):
    path = SNAPSHOT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Snapshot não encontrado")
    return FileResponse(path)


@app.post("/api/alerts/test")
async def test_alert(action: Dict[str, Any]):
    fake_event = {
        "id": f"evt_test_{uuid.uuid4().hex[:8]}",
        "timestamp": utc_iso(),
        "event_type": "manual_test",
        "rule_id": "manual_test",
        "rule_name": "Teste manual",
        "confidence": 1.0,
        "actions": [action],
        "camera_source": state.source,
    }
    frame = monitor.last_frame if monitor.last_frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)
    event = await monitor.dispatcher.dispatch(fake_event, frame, load_json(SETTINGS_FILE, DEFAULT_SETTINGS))
    return {"ok": True, "event": event}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "state", "payload": state.model_dump()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


def main():
    parser = argparse.ArgumentParser(description="Environment Monitor API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("app:app", host=args.host, port=args.port, reload=args.reload, app_dir=str(APP_DIR))


if __name__ == "__main__":
    main()
