from fastapi import FastAPI, Request, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.logic.biometric_engine import BiometricEngine
from app.db.session import get_db, init_db
from app.api.websocket_manager import manager
import time

app = FastAPI(title="GenHR Enterprise Attendance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
async def root():
    return {"status": "GenHR Enterprise API is Online", "version": "1.0.0"}

@app.websocket("/ws/live-feed")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- Biometric ADMS (Push Protocol) Endpoints ---

@app.get("/iclock/cdata")
async def adms_handshake(request: Request):
    return "OK"

@app.post("/iclock/cdata")
async def receive_biometric_data(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    raw_data = await request.body()
    data_str = raw_data.decode("utf-8")
    
    logs = BiometricEngine.parse_essl_message(data_str)
    for log in logs:
        background_tasks.add_task(BiometricEngine.process_log, db, log)
    
    return "OK"
