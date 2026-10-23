from fastapi import FastAPI

app = FastAPI(
    title="Setu API",
    description="E-commerce marketplace backend",
    version="0.1.0",
)

@app.get("/")
def root():
    return {"message": "Welcome to Setu API"}
        
@app.get("/health")
def health_check():
    return {"status": "healthy"}
