# AI Meal Scanner and Nutrition Analysis Web App

An AI + Web semester project for meal photo analysis, nutrition estimation, editable food data, and dataset building for future model training.

## 1. Project Introduction

This project uses a separated React frontend and Flask backend. Users can upload meal photos, receive multi-item food analysis, estimated portions, total calories, and nutrition summaries. The admin page lets you manage food classes, create subtypes like `cake -> chocolate_cake`, and upload training images for each label.

The current prediction logic uses a replaceable mock classifier so the site is deployable and demo-ready now, while still leaving space to plug in a real AI model later.

## 2. Features

- Meal image upload and browser preview
- Multi-item prediction response
- Estimated portion per food item
- Total calories and macro summary
- Simple diet suggestion
- Recent analysis history in backend memory
- Admin page for nutrition data editing
- Hierarchical food categories with parent category support
- Training image upload per label for future model training
- Lightweight training pipeline and trained-model switch
- Deployment-ready frontend and backend separation

## 3. Project Structure

```text
專題/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  │  └─ routes.py
│  │  ├─ core/
│  │  │  └─ config.py
│  │  ├─ data/
│  │  │  ├─ food_profiles.json
│  │  │  └─ food_profiles.py
│  │  ├─ services/
│  │  │  ├─ classifier.py
│  │  │  ├─ history_service.py
│  │  │  ├─ nutrition_service.py
│  │  │  └─ predictor.py
│  │  ├─ utils/
│  │  │  └─ image_utils.py
│  │  └─ __init__.py
│  ├─ dataset/
│  │  └─ <label folders created automatically after image upload>
│  ├─ .env.example
│  ├─ Procfile
│  ├─ requirements.txt
│  └─ run.py
├─ frontend/
│  ├─ public/
│  │  └─ _redirects
│  ├─ src/
│  │  ├─ api/
│  │  │  ├─ foodProfilesApi.js
│  │  │  └─ predictionApi.js
│  │  ├─ components/
│  │  │  ├─ FeatureGrid.jsx
│  │  │  ├─ HeroSection.jsx
│  │  │  ├─ HistorySection.jsx
│  │  │  ├─ Layout.jsx
│  │  │  ├─ MealResults.jsx
│  │  │  └─ UploadPanel.jsx
│  │  ├─ pages/
│  │  │  ├─ AdminPage.jsx
│  │  │  ├─ HomePage.jsx
│  │  │  └─ RecognitionPage.jsx
│  │  ├─ styles/
│  │  │  └─ index.css
│  │  ├─ App.jsx
│  │  └─ main.jsx
│  ├─ .env.example
│  ├─ index.html
│  ├─ package.json
│  ├─ vercel.json
│  └─ vite.config.js
├─ .gitignore
└─ README.md
```

## 4. Built-in Food Profiles

The app includes at least 12 food labels:

- rice
- fried_rice
- ramen
- sushi
- hamburger
- pizza
- salad
- steak
- sandwich
- french_fries
- fried_egg
- cake

Each profile contains:

- `display_name`
- `default_portion_label`
- `parent_category`
- `calories`
- `protein`
- `fat`
- `carbs`

Edit them here:

```text
backend/app/data/food_profiles.json
```

Or from the admin page:

```text
http://localhost:5173/admin
```

Suggested category structure:

- main category: `cake`
- sub categories: `chocolate_cake`, `cream_cake`, `cheesecake`
- main category: `rice`
- sub categories: `white_rice`, `brown_rice`, `fried_rice`, `pork_rice`

When you create a root category, leave `parent_category` empty.
When you create a subtype, set `parent_category` to the root type such as `cake` or `rice`.
Chinese labels are also supported, so you can directly use names like `蛋糕`, `巧克力蛋糕`, `白飯`, or `咖哩飯`.

## 5. Local Installation and Running

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Backend URL:

```text
http://localhost:5000
```

### Frontend

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

Main pages:

- Home: `http://localhost:5173`
- Scan: `http://localhost:5173/recognition`
- Admin: `http://localhost:5173/admin`

## 6. Frontend Deployment

### Vercel

1. Import the repo into Vercel
2. Set root directory to `frontend`
3. Add `VITE_API_BASE_URL=https://your-backend-url.onrender.com`
4. Build command: `npm run build`
5. Output directory: `dist`

### Netlify

1. Create site from Git
2. Set base directory to `frontend`
3. Build command: `npm run build`
4. Publish directory: `dist`
5. Add `VITE_API_BASE_URL=https://your-backend-url.onrender.com`

## 7. Backend Deployment

### Render

1. Create a Python web service
2. Set root directory to `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn run:app`
5. Set env vars:

```text
FLASK_ENV=production
PORT=10000
MAX_CONTENT_LENGTH=4194304
ALLOWED_EXTENSIONS=jpg,jpeg,png
CORS_ORIGINS=https://your-frontend-url.vercel.app
MODEL_PROVIDER=mock
```

### Railway

1. Create project from GitHub
2. Set service root to `backend`
3. Start command: `gunicorn run:app`
4. Add the same env vars

## 8. Environment Variables

### Backend `.env`

| Variable | Description | Example |
|---|---|---|
| `FLASK_ENV` | Running mode | `development` |
| `PORT` | Backend port | `5000` |
| `MAX_CONTENT_LENGTH` | Max upload size in bytes | `4194304` |
| `ALLOWED_EXTENSIONS` | Allowed image extensions | `jpg,jpeg,png` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173` |
| `MODEL_PROVIDER` | Classifier provider selector | `mock` |
| `TRAINED_MODEL_PATH` | Saved trained model path | `model_artifacts/meal_classifier.pkl` |

### Frontend `.env`

| Variable | Description | Example |
|---|---|---|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:5000` |

## 9. API Documentation

### `POST /predict`

Receives an image and returns multi-item meal analysis.

### `GET /health`

Returns service status.

### `GET /history`

Returns recent analysis records stored in backend memory.

### `GET /api/food-profiles`

Returns editable food profiles for the admin page.

### `POST /api/food-profiles`

Creates a new food profile.

Example JSON:

```json
{
  "label": "chocolate_cake",
  "display_name": "Chocolate Cake",
  "parent_category": "cake",
  "default_portion_label": "1 slice",
  "calories": 410,
  "protein": 5,
  "fat": 19,
  "carbs": 54
}
```

### `PUT /api/food-profiles/<label>`

Updates an existing food profile.

### `DELETE /api/food-profiles/<label>`

Deletes an existing food profile.

### `POST /api/food-profiles/<label>/images`

Uploads one or more training images for a specific label. Files are stored under:

```text
backend/dataset/<root_label>/<child_label>/
```

### `GET /api/food-profiles/<label>/images`

Returns the uploaded image file list for the selected folder.

### `DELETE /api/food-profiles/<label>/images/<filename>`

Deletes a specific uploaded training image.

### `GET /api/train/status`

Returns whether a trained model file is available.

### `POST /api/train`

Trains a lightweight classifier from the uploaded dataset images.

## 10. How the Mock AI Works

The current mock classifier:

- analyzes image color and brightness statistics
- returns 2 to 3 likely food items
- estimates a portion multiplier
- maps predicted labels to nutrition data
- calculates total calories and macro nutrients

This keeps the app demo-friendly while preserving the backend shape for a real model.

## 11. How to Replace the Mock Classifier with a Real Model

The replaceable classifier is in:

```text
backend/app/services/classifier.py
```

To upgrade it later:

1. Keep the `POST /predict` response format unchanged
2. Replace `MockFoodClassifier` with a real detector or classifier
3. Return a list of detected items with:
   - `label`
   - `confidence`
   - `portion_multiplier` or another portion estimate
4. Keep output labels consistent with keys in `backend/app/data/food_profiles.json`
5. Update classifier selection in `backend/app/services/predictor.py`

Possible future upgrades:

- YOLO or segmentation-based food detection
- real portion estimation model
- PyTorch or TensorFlow training pipeline
- persistent history storage with a database

## 12. MobileNet + Nutrition5k + Custom Dataset Architecture

The backend now includes a dedicated `app/ml/` module for a regression-based nutrition model.

Structure:

```text
backend/app/ml/
├─ datasets/
│  ├─ nutrition5k_dataset.py
│  ├─ custom_food_dataset.py
│  └─ merged_dataset.py
├─ models/
│  ├─ mobilenet_regressor.py
│  └─ losses.py
├─ training/
│  ├─ transforms.py
│  ├─ train_regression.py
│  └─ evaluate.py
└─ inference/
   └─ infer_regression.py
```

Added configuration:

- `MODEL_PROVIDER=mobilenet_regression`
- `MOBILENET_REGRESSION_MODEL_PATH=model_artifacts/mobilenet_regressor.pt`
- `MOBILENET_REGRESSION_SUMMARY_PATH=model_artifacts/training_summary.json`
- `NUTRITION5K_ROOT=dataset/nutrition5k`
- `NUTRITION5K_METADATA_PATH=app/data/nutrition5k_metadata.json`

Training workflow:

1. Put Nutrition5k images under `backend/dataset/nutrition5k/`
2. Fill `backend/app/data/nutrition5k_metadata.json` with metadata entries
3. Keep uploading your own images through the admin page
4. Run the regression training script:

```bash
cd backend
.venv\Scripts\python.exe scripts\export_training_summary.py
```

5. Change backend `.env`:

```env
MODEL_PROVIDER=mobilenet_regression
```

6. Restart backend

Inference behavior:

- The model predicts `calories`, `protein`, `fat`, and `carbs`
- The backend then matches the predicted nutrition to the closest profile in `food_profiles.json`
- The response keeps the same frontend-friendly JSON shape

## 13. Dataset Workflow for Your Own Food Types

You can now build a dataset from the admin page.

Example:

1. Create root type `cake`
2. Create subtype `chocolate_cake` with `parent_category = cake`
3. Create subtype `cream_cake` with `parent_category = cake`
4. Create subtype `cheesecake` with `parent_category = cake`
5. Open each subtype and upload many training photos
6. The backend stores them in separate folders such as:

```text
backend/dataset/cake/chocolate_cake/
backend/dataset/cake/cream_cake/
backend/dataset/cake/cheesecake/
```

You can do the same for rice:

```text
backend/dataset/rice/white_rice/
backend/dataset/rice/brown_rice/
backend/dataset/rice/fried_rice/
backend/dataset/rice/pork_rice/
```

After uploading enough images:

1. Open the admin page
2. Click `開始訓練模型`
3. Wait until training finishes
4. Change [backend/.env](C:\Users\寬\Desktop\專題\backend\.env) to:

```env
MODEL_PROVIDER=trained
```

5. Restart the backend

The site will then use your trained dataset-based classifier instead of the mock classifier.

## 14. Food-101 Classification Workflow

The project now supports a two-stage classification flow:

1. image -> food classifier
2. predicted food name -> `food_profiles.json` nutrition lookup

This means Nutrition5k does not need to recognize images in the online app. It can stay as a separate nutrition dataset or research dataset.

### Download Food-101 with PyTorch

```bash
cd backend
.venv\Scripts\python.exe scripts\download_food101.py
```

The dataset is downloaded through `torchvision.datasets.Food101` and stored under:

```text
backend/dataset/food-101/
```

### Train the classifier

```bash
cd backend
.venv\Scripts\python.exe scripts\train_food_classifier.py
```

What the classifier training now does:

- starts from a MobileNetV3 pretrained backbone
- loads mapped Food-101 classes such as `steak`, `pizza`, `hamburger`, `french_fries`, `sushi`, `ramen`, `cake`, `salad`, and others
- mixes them with your uploaded custom training images
- saves the trained model to `backend/model_artifacts/meal_classifier.pkl`

After training, keep backend `.env` set to:

```env
MODEL_PROVIDER=food_classifier
```

## 15. Quick Start Summary

### Run locally

Windows quick setup:

```bat
安裝環境.bat
啟動前後端.bat
```

`安裝環境.bat` checks Python and Node.js, creates `.env` files from the examples, creates the backend virtual environment, and installs backend/frontend packages. After it finishes, run `啟動前後端.bat` to start both servers.

Manual setup:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

### Deploy

1. Deploy backend from `backend/` to Render or Railway
2. Copy the backend public URL
3. Deploy frontend from `frontend/` to Vercel or Netlify
4. Set `VITE_API_BASE_URL` to the deployed backend URL
5. Set backend `CORS_ORIGINS` to the deployed frontend URL
