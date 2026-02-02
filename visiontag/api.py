from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import numpy as np
import cv2

from .detector import VisionTagger

app = FastAPI(title="VisionTag")

tagger = VisionTagger()


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        return JSONResponse(status_code=400, content={"tags": []})

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return JSONResponse(status_code=400, content={"tags": []})

    tags = tagger.detect(image)
    return {"tags": tags}
