# Fixed Demo Validation

Put your fixed demo images in `backend/test_cases/images/`, then copy
`demo_cases.sample.json` to `demo_cases.json` and fill in the paths and
expected labels.

Run:

```powershell
cd C:\Users\寬\Desktop\專題\backend
& ".\.venv\Scripts\python.exe" scripts\run_fixed_validation.py
```

Each case should look like:

```json
{
  "name": "fried-rice-demo",
  "image_path": "images/fried-rice.jpg",
  "expected_any_of": ["炒飯", "fried rice"]
}
```

Result statuses:

- `pass`: the main predicted result matches one of the expected labels
- `candidate_only`: the expected label only appeared in alternatives
- `fail`: no expected label appeared
- `missing`: the image path could not be found
