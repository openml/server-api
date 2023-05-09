from fastapi import FastAPI

app = FastAPI()


@app.get("/dataset/{dataset_id}")
def get_dataset(dataset_id: int) -> dict[str, int]:
    return {"dataset_id": dataset_id}
