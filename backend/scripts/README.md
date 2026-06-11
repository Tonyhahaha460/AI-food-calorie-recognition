# Training Scripts

Current active model files:

- All-food image classifier: `backend/runs/all_food_cls/uec_food101_yolov8n_cls-3/weights/best.pt`
- Legacy local classifier: `../local_assets/backend/model_artifacts/meal_classifier.pkl`
- Nutrition regressor: `../local_assets/backend/model_artifacts/mobilenet_regressor.pt`

Current active scripts:

- `train_nutrition5k_mobilenet_spyder.py`: retrains the Nutrition5k calorie/protein/fat/carbs regressor.
- `prepare_nutrition5k.py`: rebuilds Nutrition5k metadata if the Nutrition5k dataset changes.
- `run_fixed_validation.py`: validation helper.

Removed scripts:

- Food-101-only and UEC-Food100-only training scripts were removed because their source image folders were deleted after producing `best.pt`.
- The all-food rebuild script was removed because `圖片/all_food` and the source UEC/Food-101 images are no longer kept locally.

To retrain the all-food classifier, download UEC-Food100 and Food-101 again, rebuild `圖片/all_food`, then train a new YOLOv8 classification run.
