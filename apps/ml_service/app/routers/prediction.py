from fastapi import APIRouter, HTTPException, Request


from app.schemas.prediction_schema import (
    DemandPredictionRequest, 
    DemandPredictionResponse, 
    DemandPredictionResult, 
)


router = APIRouter(
    prefix="/predictions", 
    tags=["Demand Predictions"], 
)


@router.post("/demand", response_model=DemandPredictionResponse)
def predict_demand(request_body: DemandPredictionRequest, request: Request):
    prediction_service = request.app.state.prediction_service
    settings = request.app.state.settings

    try:
        predicted_values = prediction_service.predict_batch(request_body.items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    predictions = [
        DemandPredictionResult(
            candidate_price=item.candidate_price,
            expected_sales=float(value),
        )
        for item, value in zip(request_body.items, predicted_values)
    ]

    return DemandPredictionResponse(
        model_name=settings.model_name,
        n_fold_models=len(prediction_service.bundle.model_paths),
        predictions=predictions,
    )