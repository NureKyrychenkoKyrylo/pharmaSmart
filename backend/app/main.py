from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.routers import auth_router, pharmacies_router, inventory_router, iot_router, sales_router, admin_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PharmaSmart API",
    version="1.0.0",
    description="API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(pharmacies_router.router, prefix="/pharmacies", tags=["Pharmacies"])
app.include_router(inventory_router.router, prefix="/inventory", tags=["Inventory"])
app.include_router(iot_router.router, prefix="/iot", tags=["IoT Monitoring"])
app.include_router(sales_router.router, prefix="/sales", tags=["Sales (Business Logic)"])
app.include_router(admin_router.router, prefix="/admin", tags=["Administration"])

@app.get("/")
def root():
    return {"message": "PharmaSmart API is running"}
